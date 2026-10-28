import json
import logging

from groq import AsyncGroq, BadRequestError
from pydantic import ValidationError

from settings import settings

from .changes import Fact, MemoryChanges

logger = logging.getLogger("sarjy.memory")

PROMPT = """You maintain a voice assistant's long-term memory of one user. You never answer the user.
You get the facts already known and the latest turns of a conversation between the user and
Sarjy, the assistant. Use Sarjy's lines only as context. Return the changes to make:
- set: durable facts or preferences the user states about themselves (e.g. name, favorite color,
  home city, foods they like or dislike). Keys are snake_case. For a fact that changes, reuse its
  existing key with the new value. If the user corrects themselves, keep the final value.
- remove: keys of known facts the user contradicts or asks you to forget. When a new fact
  replaces an old one under a different key (dislikes_milk -> likes_milk), remove the old key.
Store the user's name under "name". The assistant is named Sarjy (speech-to-text may spell it
"Sergei", "Sergey", "Sarji"): a name the user addresses ("Hey, Sergei") is the assistant's, never
the user's.
Ignore one-off details like what the user ate today or a food they asked about. Questions and
small talk change nothing: respond {"set": [], "remove": []}.

Known facts: """

SCHEMA = MemoryChanges.model_json_schema()

# More changes than a conversation plausibly makes means a confused reply, not new facts.
MAX_CHANGES = 10
# A longer "name" is a sentence the extractor misread, and the greeting would say it aloud.
MAX_NAME_WORDS = 3


async def extract_changes(conversation: str, known: dict[str, str]) -> MemoryChanges:
    client = AsyncGroq(api_key=settings.groq_api_key.get_secret_value())
    try:
        response = await client.chat.completions.create(
            model="openai/gpt-oss-20b",
            reasoning_effort="low",
            messages=[
                {"role": "system", "content": PROMPT + json.dumps(known)},
                {"role": "user", "content": conversation},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "memory_changes", "strict": True, "schema": SCHEMA},
            },
            temperature=0,
        )
    except BadRequestError as error:
        # The model sometimes replies with nothing for small talk, which Groq's schema check
        # rejects. Nothing to remember in that case.
        if "json_validate_failed" in str(error):
            return MemoryChanges.none()
        raise
    return parse_changes(response.choices[0].message.content or "", known)


def parse_changes(reply: str, known: dict[str, str]) -> MemoryChanges:
    """The extractor's reply as changes safe to apply; anything suspicious changes nothing."""
    try:
        changes = MemoryChanges.model_validate_json(reply)
    except ValidationError:
        logger.warning("ignored malformed memory changes: %r", reply)
        return MemoryChanges.none()
    facts = [fact for fact in changes.set if _is_valid(fact)]
    removals = [key for key in changes.remove if key in known]
    if len(facts) + len(removals) > MAX_CHANGES:
        logger.warning("ignored %d memory changes at once: %r", len(facts) + len(removals), reply)
        return MemoryChanges.none()
    return MemoryChanges(set=facts, remove=removals)


def _is_valid(fact: Fact) -> bool:
    if not fact.key.strip() or not fact.value.strip():
        return False
    if fact.key == "name" and len(fact.value.split()) > MAX_NAME_WORDS:
        logger.warning("ignored implausible name: %r", fact.value)
        return False
    return True

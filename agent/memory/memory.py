import asyncio
import logging

from livekit.agents import AgentSession, ConversationItemAddedEvent, utils

from . import db
from .changes import Fact, MemoryChanges
from .llm_extractor import extract_facts

logger = logging.getLogger("sarjy.memory")


class UserMemory:
    """Facts Sarjy remembers about one user, kept in sync with the database."""

    def __init__(self, user_id: str, facts: dict[str, str]):
        self.user_id = user_id
        self.facts = facts
        # Keeps background tasks referenced so they aren't garbage-collected mid-run.
        self._tasks = utils.aio.TaskSet()
        # Processes turns one at a time, so a later fact can't be overwritten by an earlier one.
        self._lock = asyncio.Lock()

    @classmethod
    async def load(cls, user_id: str) -> UserMemory:
        facts = await db.load_facts(user_id)
        logger.info("loaded %d facts for user %s", len(facts), user_id)
        return cls(user_id, facts)

    def as_prompt(self) -> str:
        if not self.facts:
            return ""
        remembered = "\n".join(f"- {key}: {value}" for key, value in self.facts.items())
        return f"\n\nWhat you know about the user:\n{remembered}"

    def listen(self, session: AgentSession) -> None:
        """Remembers facts from every user message in the session, spoken or typed."""
        session.on("conversation_item_added", self._on_conversation_item_added)

    def _on_conversation_item_added(self, event: ConversationItemAddedEvent) -> None:
        message = event.item
        if message.type == "message" and message.role == "user" and message.text_content:
            self._tasks.create_task(self._remember(message.text_content))

    async def wait_for_pending(self) -> None:
        await asyncio.gather(*self._tasks.tasks)

    async def _remember(self, text: str) -> None:
        async with self._lock:
            try:
                new_facts = await extract_facts(text, self.facts)
                if new_facts:
                    changes = MemoryChanges(
                        set=[Fact(key=k, value=v) for k, v in new_facts.items()]
                    )
                    await db.apply_changes(self.user_id, changes)
                    self.facts.update(new_facts)
                    logger.info("remembered facts: %s", new_facts)
            except Exception:
                logger.exception("failed to remember facts")

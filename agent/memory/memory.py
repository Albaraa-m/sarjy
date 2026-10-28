import asyncio
import logging

from livekit.agents import AgentSession, ConversationItemAddedEvent, llm, utils

from . import db
from .llm_extractor import extract_changes

logger = logging.getLogger("sarjy.memory")

# Long calls are also remembered along the way, so the end-of-call extraction stays small and a
# call that ends badly loses at most this many turns.
CHECKPOINT_USER_TURNS = 10
SPEAKERS = {"user": "User", "assistant": "Sarjy"}


class UserMemory:
    """Facts Sarjy remembers about one user, kept in sync with the database."""

    def __init__(self, user_id: str, facts: dict[str, str]):
        self.user_id = user_id
        self.facts = facts
        self._unsent: list[llm.ChatMessage] = []
        # Keeps background tasks referenced so they aren't garbage-collected mid-run.
        self._tasks = utils.aio.TaskSet()
        # Extracts one batch at a time, so a later change can't be overwritten by an earlier one.
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
        """Collects the conversation, remembering it every few user turns."""
        session.on("conversation_item_added", self._on_conversation_item_added)

    async def remember_rest(self) -> None:
        """Remembers the turns since the last checkpoint. Call it once the conversation ends."""
        rest = self._take_unsent()
        # A checkpoint created just before may not have started yet; its older turns go first.
        await asyncio.gather(*self._tasks.tasks)
        await self._remember(rest)

    def _on_conversation_item_added(self, event: ConversationItemAddedEvent) -> None:
        message = event.item
        if message.type != "message" or message.role not in SPEAKERS or not message.text_content:
            return
        self._unsent.append(message)
        if sum(turn.role == "user" for turn in self._unsent) >= CHECKPOINT_USER_TURNS:
            self._tasks.create_task(self._remember(self._take_unsent()))

    def _take_unsent(self) -> list[llm.ChatMessage]:
        turns, self._unsent = self._unsent, []
        return turns

    async def _remember(self, turns: list[llm.ChatMessage]) -> None:
        if not any(turn.role == "user" for turn in turns):
            return
        conversation = "\n".join(
            f"{SPEAKERS[turn.role]}: {(turn.text_content or '').strip()}" for turn in turns
        )
        async with self._lock:
            try:
                changes = await extract_changes(conversation, self.facts)
                if changes:
                    await db.apply_changes(self.user_id, changes)
                    changes.apply_to(self.facts)
                    logger.info("memory changes: %s", changes)
            except Exception:
                logger.exception("failed to remember facts")

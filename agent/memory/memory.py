import asyncio
import logging

from livekit.agents import utils

from . import db
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
        return cls(user_id, await db.load_facts(user_id))

    def as_prompt(self) -> str:
        if not self.facts:
            return ""
        remembered = "\n".join(f"- {key}: {value}" for key, value in self.facts.items())
        return f"\n\nWhat you remember about the user from past conversations:\n{remembered}"

    def remember_in_background(self, text: str) -> None:
        self._tasks.create_task(self._remember(text))

    async def wait_for_pending(self) -> None:
        await asyncio.gather(*self._tasks.tasks)

    async def _remember(self, text: str) -> None:
        async with self._lock:
            try:
                new_facts = await extract_facts(text, self.facts)
                if new_facts:
                    await db.save_facts(self.user_id, new_facts)
                    self.facts.update(new_facts)
                    logger.info("remembered facts: %s", new_facts)
            except Exception:
                logger.exception("failed to remember facts")

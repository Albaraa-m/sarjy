import asyncio
import logging
import os

import asyncpg
from livekit.agents import utils

from extraction import extract_facts

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
        conn = await asyncpg.connect(os.environ["DATABASE_URL"])
        try:
            rows = await conn.fetch("select key, value from memories where user_id = $1", user_id)
        finally:
            await conn.close()
        return cls(user_id, {row["key"]: row["value"] for row in rows})

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
                await self._save(new_facts)
                self.facts.update(new_facts)
                if new_facts:
                    logger.info("remembered facts: %s", new_facts)
            except Exception:
                logger.exception("failed to remember facts")

    async def _save(self, facts: dict[str, str]) -> None:
        if not facts:
            return
        conn = await asyncpg.connect(os.environ["DATABASE_URL"])
        try:
            # Upsert: a new value for an existing key overwrites the old one.
            await conn.executemany(
                """
                insert into memories (user_id, key, value) values ($1, $2, $3)
                on conflict (user_id, key) do update set value = excluded.value, updated_at = now()
                """,
                [(self.user_id, key, value) for key, value in facts.items()],
            )
        finally:
            await conn.close()

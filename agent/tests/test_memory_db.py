import asyncpg
import pytest

from memory import db as memory_db
from memory.changes import Fact, MemoryChanges


async def test_sets_and_removes_facts(user_id):
    await memory_db.apply_changes(
        user_id, MemoryChanges(set=[Fact(key="dislikes_milk", value="yes")], remove=[])
    )
    await memory_db.apply_changes(
        user_id,
        MemoryChanges(set=[Fact(key="likes_milk", value="yes")], remove=["dislikes_milk"]),
    )
    assert await memory_db.load_facts(user_id) == {"likes_milk": "yes"}


async def test_a_failed_set_keeps_the_removed_facts(user_id):
    await memory_db.apply_changes(
        user_id, MemoryChanges(set=[Fact(key="city", value="Riyadh")], remove=[])
    )
    # Postgres rejects NUL bytes in text, failing the insert after the delete ran.
    with pytest.raises(asyncpg.PostgresError):
        await memory_db.apply_changes(
            user_id,
            MemoryChanges(set=[Fact(key="city", value="Jeddah\x00")], remove=["city"]),
        )
    assert await memory_db.load_facts(user_id) == {"city": "Riyadh"}

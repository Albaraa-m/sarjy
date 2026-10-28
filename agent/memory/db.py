import database

from .changes import MemoryChanges


async def load_facts(user_id: str) -> dict[str, str]:
    pool = await database.pool()
    rows = await pool.fetch("select key, value from memories where user_id = $1", user_id)
    return {row["key"]: row["value"] for row in rows}


async def apply_changes(user_id: str, changes: MemoryChanges) -> None:
    """Applies all of the changes or, if any statement fails, none of them."""
    pool = await database.pool()
    async with pool.acquire() as connection, connection.transaction():
        await connection.execute(
            "delete from memories where user_id = $1 and key = any($2::text[])",
            user_id,
            changes.remove,
        )
        await connection.executemany(
            """
            insert into memories (user_id, key, value) values ($1, $2, $3)
            on conflict (user_id, key) do update set value = excluded.value, updated_at = now()
            """,
            [(user_id, fact.key, fact.value) for fact in changes.set],
        )

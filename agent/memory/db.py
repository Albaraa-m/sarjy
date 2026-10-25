import os

import asyncpg


async def load_facts(user_id: str) -> dict[str, str]:
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        rows = await conn.fetch("select key, value from memories where user_id = $1", user_id)
    finally:
        await conn.close()
    return {row["key"]: row["value"] for row in rows}


async def save_facts(user_id: str, facts: dict[str, str]) -> None:
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        # Upsert: a new value for an existing key overwrites the old one.
        await conn.executemany(
            """
            insert into memories (user_id, key, value) values ($1, $2, $3)
            on conflict (user_id, key) do update set value = excluded.value, updated_at = now()
            """,
            [(user_id, key, value) for key, value in facts.items()],
        )
    finally:
        await conn.close()

import database


async def load_facts(user_id: str) -> dict[str, str]:
    pool = await database.pool()
    rows = await pool.fetch("select key, value from memories where user_id = $1", user_id)
    return {row["key"]: row["value"] for row in rows}


async def save_facts(user_id: str, facts: dict[str, str]) -> None:
    pool = await database.pool()
    await pool.executemany(
        """
        insert into memories (user_id, key, value) values ($1, $2, $3)
        on conflict (user_id, key) do update set value = excluded.value, updated_at = now()
        """,
        [(user_id, key, value) for key, value in facts.items()],
    )

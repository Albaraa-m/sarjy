import os
from datetime import date

import asyncpg


async def add_food(
    user_id: str,
    day: date,
    food: str,
    grams: float,
    calories: float,
    protein_g: float,
    carbs_g: float,
    fat_g: float,
    source: str,
) -> None:
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        await conn.execute(
            """
            insert into food_log
                (user_id, eaten_on, food, grams, calories, protein_g, carbs_g, fat_g, source)
            values ($1, $2, $3, $4, $5, $6, $7, $8, $9)
            """,
            user_id,
            day,
            food,
            grams,
            calories,
            protein_g,
            carbs_g,
            fat_g,
            source,
        )
    finally:
        await conn.close()


async def foods_on(user_id: str, day: date) -> list[dict]:
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        rows = await conn.fetch(
            """
            select food, grams, calories, protein_g, carbs_g, fat_g, source from food_log
            where user_id = $1 and eaten_on = $2 order by created_at
            """,
            user_id,
            day,
        )
    finally:
        await conn.close()
    return [dict(row) for row in rows]

from datetime import date

import database

from .nutrition import Macros, Portion


async def save(user_id: str, day: date, portions: list[Portion]) -> None:
    """Saves all portions or, if anything fails, none of them."""
    pool = await database.pool()
    async with pool.acquire() as conn, conn.transaction():
        await conn.executemany(
            """
            insert into food_log
                (user_id, eaten_on, food, display_name, grams, calories, protein_g, carbs_g, fat_g,
                 source)
            values ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            """,
            [
                (
                    user_id,
                    day,
                    portion.usda_description or portion.name,
                    portion.name,
                    portion.grams,
                    portion.macros.calories,
                    portion.macros.protein_g,
                    portion.macros.carbs_g,
                    portion.macros.fat_g,
                    portion.source,
                )
                for portion in portions
            ],
        )


async def eaten_on(user_id: str, day: date) -> list[Portion]:
    """The user's portions for `day`, oldest first."""
    pool = await database.pool()
    rows = await pool.fetch(
        """
        select food, display_name, grams, calories, protein_g, carbs_g, fat_g, source from food_log
        where user_id = $1 and eaten_on = $2 order by id
        """,
        user_id,
        day,
    )
    return [
        Portion(
            # Rows saved before display names existed show their USDA description.
            name=row["display_name"] or row["food"],
            usda_description=row["food"] if row["source"] == "usda" else None,
            grams=row["grams"],
            macros=Macros(row["calories"], row["protein_g"], row["carbs_g"], row["fat_g"]),
            source=row["source"],
        )
        for row in rows
    ]

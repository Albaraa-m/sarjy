from datetime import date

import database

from .nutrition import FoodEntry, Macros


async def add_food(user_id: str, day: date, entry: FoodEntry) -> None:
    pool = await database.pool()
    await pool.execute(
        """
        insert into food_log
            (user_id, eaten_on, food, grams, calories, protein_g, carbs_g, fat_g, source)
        values ($1, $2, $3, $4, $5, $6, $7, $8, $9)
        """,
        user_id,
        day,
        entry.food,
        entry.grams,
        entry.macros.calories,
        entry.macros.protein_g,
        entry.macros.carbs_g,
        entry.macros.fat_g,
        entry.source,
    )


async def foods_on(user_id: str, day: date) -> list[FoodEntry]:
    """The user's entries for `day`, oldest first."""
    pool = await database.pool()
    rows = await pool.fetch(
        """
        select food, grams, calories, protein_g, carbs_g, fat_g, source from food_log
        where user_id = $1 and eaten_on = $2 order by id
        """,
        user_id,
        day,
    )
    return [
        FoodEntry(
            food=row["food"],
            grams=row["grams"],
            macros=Macros(row["calories"], row["protein_g"], row["carbs_g"], row["fat_g"]),
            source=row["source"],
        )
        for row in rows
    ]

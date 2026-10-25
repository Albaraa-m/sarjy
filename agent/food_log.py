import os
from datetime import date, datetime
from zoneinfo import ZoneInfo

import asyncpg

# The agent runs in UTC, but "today" should follow the user's day in Saudi Arabia.
TIMEZONE = ZoneInfo("Asia/Riyadh")
MACROS = ("calories", "protein_g", "carbs_g", "fat_g")


class FoodLog:
    """What one user ate, grouped by day."""

    def __init__(self, user_id: str):
        self.user_id = user_id

    async def add(
        self,
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
                self.user_id,
                _today(),
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

    async def today(self) -> dict:
        conn = await asyncpg.connect(os.environ["DATABASE_URL"])
        try:
            rows = await conn.fetch(
                """
                select food, grams, calories, protein_g, carbs_g, fat_g, source from food_log
                where user_id = $1 and eaten_on = $2 order by created_at
                """,
                self.user_id,
                _today(),
            )
        finally:
            await conn.close()
        entries = [dict(row) for row in rows]
        totals = {macro: round(sum(entry[macro] for entry in entries), 1) for macro in MACROS}
        return {"totals": totals, "entries": entries}


def _today() -> date:
    return datetime.now(TIMEZONE).date()

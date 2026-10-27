import json
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from . import db
from .nutrition import FoodEntry, Macros, Nutrition

# "Today" is the user's day in Saudi Arabia, not the server's (UTC) day.
TIMEZONE = ZoneInfo("Asia/Riyadh")
# Demo targets, not personalized advice; the UI labels them as such.
DAILY_TARGETS = Macros(calories=2200, protein_g=150, carbs_g=220, fat_g=70)


@dataclass(frozen=True)
class DaySummary:
    day: date
    entries: list[FoodEntry]
    pending: FoodEntry | None
    totals: Macros
    targets: Macros
    remaining: Macros

    def to_json(self) -> str:
        """The shape the web "Today" panel parses (web/lib/parse-nutrition-summary.ts)."""
        return json.dumps({**asdict(self), "day": self.day.isoformat()})


class FoodLog:
    """One user's food log for today. A food is first prepared (pending), and saved only once
    confirmed. Today's entries are kept in memory, so only confirming touches the database.
    Every change is reported through `on_change`, e.g. to update the UI."""

    def __init__(
        self,
        user_id: str,
        nutrition: Nutrition,
        on_change: Callable[[DaySummary], Awaitable[None]],
        day: date,
        entries: list[FoodEntry],
    ):
        self.user_id = user_id
        self.nutrition = nutrition
        self._on_change = on_change
        # A call that runs past midnight keeps logging to the day it started.
        self.day = day
        self._entries = entries
        self._pending: FoodEntry | None = None

    @classmethod
    async def load(
        cls,
        user_id: str,
        nutrition: Nutrition,
        on_change: Callable[[DaySummary], Awaitable[None]],
    ) -> FoodLog:
        day = today()
        return cls(user_id, nutrition, on_change, day, await db.foods_on(user_id, day))

    async def prepare(self, match_id: int, grams: float) -> DaySummary | None:
        """Makes a looked-up USDA food the pending entry. None if that id was never looked up."""
        match = self.nutrition.match(match_id)
        if match is None:
            return None
        entry = FoodEntry(match.description, grams, match.per_100g.scaled(grams), "usda")
        return await self._set_pending(entry)

    async def prepare_estimate(self, food: str, grams: float, macros: Macros) -> DaySummary:
        return await self._set_pending(FoodEntry(food, grams, macros, "estimate"))

    async def confirm(self) -> DaySummary | None:
        """Saves the pending entry. None if nothing is pending, so a repeated yes can't save twice.
        If saving fails, the entry stays pending, so the user can say yes again."""
        if self._pending is None:
            return None
        await db.add_food(self.user_id, self.day, self._pending)
        self._entries.append(self._pending)
        return await self._set_pending(None)

    async def cancel(self) -> DaySummary:
        return await self._set_pending(None)

    def summary(self) -> DaySummary:
        totals = _sum(entry.macros for entry in self._entries)
        remaining = Macros(
            calories=max(round(DAILY_TARGETS.calories - totals.calories, 1), 0),
            protein_g=max(round(DAILY_TARGETS.protein_g - totals.protein_g, 1), 0),
            carbs_g=max(round(DAILY_TARGETS.carbs_g - totals.carbs_g, 1), 0),
            fat_g=max(round(DAILY_TARGETS.fat_g - totals.fat_g, 1), 0),
        )
        return DaySummary(
            self.day, list(self._entries), self._pending, totals, DAILY_TARGETS, remaining
        )

    async def _set_pending(self, entry: FoodEntry | None) -> DaySummary:
        self._pending = entry
        summary = self.summary()
        await self._on_change(summary)
        return summary


def today() -> date:
    return riyadh_day(datetime.now(UTC))


def riyadh_day(instant: datetime) -> date:
    return instant.astimezone(TIMEZONE).date()


def _sum(all_macros: Iterable[Macros]) -> Macros:
    total = Macros(0, 0, 0, 0)
    for macros in all_macros:
        total = Macros(
            calories=round(total.calories + macros.calories, 1),
            protein_g=round(total.protein_g + macros.protein_g, 1),
            carbs_g=round(total.carbs_g + macros.carbs_g, 1),
            fat_g=round(total.fat_g + macros.fat_g, 1),
        )
    return total

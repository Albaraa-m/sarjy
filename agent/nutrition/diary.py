from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from . import db
from .models import NO_MACROS, DailyIntake, Macros, Portion
from .nutrition import Nutrition

# "Today" is the user's day in Saudi Arabia, not the server's (UTC) day.
TIMEZONE = ZoneInfo("Asia/Riyadh")
# Demo targets, not personalized advice; the UI labels them as such.
DAILY_TARGETS = Macros(calories=2200, protein_g=150, carbs_g=220, fat_g=70)


class Diary:
    """One user's food diary for today. Portions are first proposed (pending), and saved together
    once confirmed. Today's eaten portions are kept in memory, so only confirming touches the
    database. Every change is reported through `on_change`, e.g. to update the UI."""

    def __init__(
        self,
        user_id: str,
        nutrition: Nutrition,
        on_change: Callable[[DailyIntake], Awaitable[None]],
        day: date,
        eaten: list[Portion],
    ):
        self.user_id = user_id
        self.nutrition = nutrition
        self._on_change = on_change
        # A call that runs past midnight keeps logging to the day it started.
        self.day = day
        self._eaten = eaten
        self._pending: list[Portion] = []

    @classmethod
    async def load(
        cls,
        user_id: str,
        nutrition: Nutrition,
        on_change: Callable[[DailyIntake], Awaitable[None]],
    ) -> Diary:
        day = today()
        return cls(user_id, nutrition, on_change, day, await db.eaten_on(user_id, day))

    async def propose(self, fdc_id: int, grams: float, name: str) -> DailyIntake | None:
        """Adds a looked-up USDA food to the pending portions. None if it was never looked up."""
        usda_food = self.nutrition.usda_food(fdc_id)
        if usda_food is None:
            return None
        macros = usda_food.per_100g.scaled(grams)
        return await self._add_pending(
            Portion(
                name=name,
                usda_description=usda_food.description,
                grams=grams,
                macros=macros,
                source="usda",
            )
        )

    async def propose_estimate(self, name: str, grams: float, macros: Macros) -> DailyIntake:
        return await self._add_pending(
            Portion(name=name, usda_description=None, grams=grams, macros=macros, source="estimate")
        )

    async def confirm(self) -> DailyIntake | None:
        """Saves all pending portions. None if nothing is pending, so a repeated yes can't save
        twice. If saving fails, the portions stay pending, so the user can say yes again."""
        portions = self._pending
        if not portions:
            return None
        # Taken before the await, so a parallel confirm call finds nothing to save.
        self._pending = []
        try:
            await db.save(self.user_id, self.day, portions)
        except Exception:
            self._pending = portions + self._pending
            raise
        self._eaten.extend(portions)
        return await self._changed()

    async def cancel(self, name: str | None = None) -> DailyIntake | None:
        """Drops the pending portion called `name` (its name or USDA description, any case), or
        all pending portions when None. None if no pending portion has that name."""
        if name is None:
            self._pending = []
        else:
            kept = [portion for portion in self._pending if not _is_called(portion, name)]
            if len(kept) == len(self._pending):
                return None
            self._pending = kept
        return await self._changed()

    def intake(self) -> DailyIntake:
        totals = sum((portion.macros for portion in self._eaten), NO_MACROS)
        return DailyIntake(
            day=self.day,
            eaten=list(self._eaten),
            pending=list(self._pending),
            totals=totals,
            targets=DAILY_TARGETS,
            remaining=DAILY_TARGETS.remaining_after(totals),
        )

    async def _add_pending(self, portion: Portion) -> DailyIntake:
        # Proposing a pending food again replaces it ("actually, two eggs").
        self._pending = [pending for pending in self._pending if not _same_food(pending, portion)]
        self._pending.append(portion)
        return await self._changed()

    async def _changed(self) -> DailyIntake:
        intake = self.intake()
        await self._on_change(intake)
        return intake


def today() -> date:
    return riyadh_day(datetime.now(UTC))


def riyadh_day(instant: datetime) -> date:
    return instant.astimezone(TIMEZONE).date()


def _same_food(a: Portion, b: Portion) -> bool:
    # The LLM may name the same USDA food differently ("Eggs", then "Scrambled eggs").
    return (a.usda_description or a.name) == (b.usda_description or b.name)


def _is_called(portion: Portion, name: str) -> bool:
    # The LLM cancels by the name it gave the food ("Milk"), not USDA's ("Milk, whole").
    names = (portion.name, portion.usda_description or "")
    return name.casefold() in (known.casefold() for known in names)

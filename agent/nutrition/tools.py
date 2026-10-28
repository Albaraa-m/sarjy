import asyncio
import logging
import random
from collections.abc import Awaitable, Callable

import httpx
from livekit.agents import RunContext, ToolError, function_tool, llm
from livekit.agents.voice import SpeechHandle
from pydantic import BaseModel, ValidationError

from . import usda
from .diary import Diary
from .models import Macros, Portion, UsdaFood

logger = logging.getLogger("sarjy.nutrition")

INSTRUCTIONS = """
- Nutrition: calories and macros for foods.
Always call lookup_nutrition for numbers, never memory, and don't announce the lookup. Mention the USDA in every answer with numbers, casually. If it's not found, say so and give a labeled estimate.

Examples:
User: how much protein in chicken breast
Sarjy: Oh, a lot. USDA says about 47 grams for a regular cooked breast.

User: and fat?
Sarjy: Barely any, like 5 grams.

User: calories in a banana
Sarjy: USDA has a medium one at about 105.

User: two eggs and a slice of toast
Sarjy: Hmm, around 230 all in, says the USDA.

User: calories in a plate of kabsa
Sarjy: Depends how big. Normal plate or a big one?

User: how many calories in Al Baik broast
Sarjy: USDA doesn't have Al Baik, sadly. Similar fried chicken's roughly 900, so take that as a guess.

User: is greek yogurt good for my protein goal
Sarjy: Yeah, really good. USDA says about 23 grams a cup, so almost a fifth of your 120.

- Food log: what the user ate today, against daily targets.
Log only when the user says they ate or had something; a question is just a lookup. To log: look
up every food they name, pick the USDA food that fits each, and call propose_portion once per food in
the same turn, before you ask anything: the user sees the pending foods on screen while you read
them back as one short list with the total calories and ask whether to log them. One clear yes
saves them all with confirm_portions; on no, call cancel_portions; to drop one food ("but no
milk"), cancel it by name, then confirm the rest; if they change a food or amount, propose it
again. For a countable food (a banana, a burrito) assume a normal one and say so; otherwise ask
how much. If USDA doesn't have it, propose your own estimate with propose_estimated_portion, also
before asking, and say it's an estimate. For anything about what they've eaten or have left today, call
get_daily_intake first.

Examples:
User: I had a banana this morning
Sarjy: A medium banana, about 105 calories per USDA. Want me to log it?

User: yes
Sarjy: Done, you're at 1,200 of 2,200 calories today.

User: breakfast was three eggs, two slices of toast and a cup of milk
Sarjy: Three eggs, two slices of toast and a cup of milk, about 540 calories per USDA. Log all of it?

User: I ate a plate of kabsa
Sarjy: USDA doesn't have kabsa, so my estimate for a normal plate is about 700 calories. Log that?"""

# Said only when a lookup is slow, so quick answers come without filler.
FILLER_DELAY_S = 0.6
# After a filler, answer no sooner than this, so it sounds like Sarjy actually looked it up.
MIN_LOOKUP_AFTER_FILLER_S = 1.2
FILLERS = (
    "Hmm, let me check.",
    "Oh, one sec.",
    "Let me pull that up.",
    "Good question, one sec.",
    "Hang on, checking.",
    "Let me see.",
    "Uh, give me a sec.",
    "Okay, looking it up.",
)


class ScaledFood(BaseModel):
    fdc_id: int
    description: str
    macros: Macros


class LookupResult(BaseModel):
    grams: float
    # Empty when USDA doesn't have the food.
    foods: list[ScaledFood]


class NutritionToolset(llm.Toolset):
    """The nutrition tools the LLM can call, plus the instructions for using them.
    Each tool returns JSON (LiveKit sends a tool's result to the LLM as a string)."""

    instructions = INSTRUCTIONS

    def __init__(
        self,
        diary: Diary,
        search: Callable[[str], Awaitable[list[UsdaFood]]] = usda.search,
    ):
        super().__init__(id="nutrition")
        self.diary = diary
        self._search = search
        # Only foods the LLM was shown can be proposed, so it can't invent an id or its macros.
        self._usda_foods: dict[int, UsdaFood] = {}
        self._filler: SpeechHandle | None = None

    @function_tool
    async def lookup_nutrition(self, context: RunContext, query: str, grams: float) -> str:
        """Looks up calories and macros for an amount of food in USDA's database.

        Args:
            query: A generic food name, e.g. "chicken breast cooked" or "white rice cooked".
            grams: The amount in grams.
        """
        try:
            usda_foods = await self._with_filler(context, self._search(query))
        except (httpx.HTTPError, ValidationError) as error:
            raise ToolError("USDA is unavailable; give a labeled estimate.") from error
        self._usda_foods.update({food.fdc_id: food for food in usda_foods})
        foods = [
            ScaledFood(
                fdc_id=food.fdc_id, description=food.description, macros=food.per_100g.scaled(grams)
            )
            for food in usda_foods
        ]
        return LookupResult(grams=grams, foods=foods).model_dump_json()

    @function_tool
    async def propose_portion(self, fdc_id: int, grams: float, name: str) -> str:
        """Proposes logging one food the user ate, using a USDA food from lookup_nutrition; call
        it once per food, right after the lookups, before asking whether to log them. Nothing is
        saved until confirm_portions; the user sees the foods as pending.

        Args:
            fdc_id: The fdc_id of the lookup_nutrition food that fits what the user ate.
            grams: The amount the user ate, in grams.
            name: The food as the user would say it, shown on screen, in sentence case, e.g.
                "Banana", "Big Mac", "Beef burrito"; never USDA's description.
        """
        usda_food = self._usda_foods.get(fdc_id)
        if usda_food is None:
            raise ToolError("Call lookup_nutrition first, then use one of its fdc_ids.")
        intake = await self.diary.propose(usda_food.portion(grams, name))
        return intake.model_dump_json()

    @function_tool
    async def propose_estimated_portion(
        self,
        name: str,
        grams: float,
        calories: float,
        protein_g: float,
        carbs_g: float,
        fat_g: float,
    ) -> str:
        """Proposes logging a food USDA doesn't have, with your own estimate for that amount.
        Saved only after confirm_portions, and marked as an estimate.

        Args:
            name: What the user ate, shown on screen, in sentence case, e.g. "Chicken kabsa".
            grams: The amount the user ate, in grams.
            calories: Your estimate for that amount.
            protein_g: Your estimate for that amount.
            carbs_g: Your estimate for that amount.
            fat_g: Your estimate for that amount.
        """
        macros = Macros(calories=calories, protein_g=protein_g, carbs_g=carbs_g, fat_g=fat_g)
        portion = Portion(
            name=name, usda_description=None, grams=grams, macros=macros, source="estimate"
        )
        intake = await self.diary.propose(portion)
        return intake.model_dump_json()

    @function_tool
    async def confirm_portions(self) -> str:
        """Saves all pending foods. Call only after the user clearly says yes to logging them."""
        try:
            intake = await self.diary.confirm()
        except Exception as error:
            logger.exception("saving pending portions failed")
            raise ToolError("Couldn't save; ask the user to try again.") from error
        # Nothing was pending, e.g. a repeated yes: saving again would log the foods twice.
        return (intake or self.diary.intake()).model_dump_json()

    @function_tool
    async def cancel_portions(self, name: str = "") -> str:
        """Drops pending foods the user doesn't want logged.

        Args:
            name: The name you gave the food in propose_portion, to drop just that one; empty
                to drop all pending foods.
        """
        intake = await self.diary.cancel(name or None)
        if intake is None:
            pending = ", ".join(portion.name for portion in self.diary.intake().pending)
            raise ToolError(f"No pending food is called {name!r}. Pending: {pending or 'none'}.")
        return intake.model_dump_json()

    @function_tool
    async def get_daily_intake(self) -> str:
        """Today's logged foods, totals, demo targets and what's remaining."""
        return self.diary.intake().model_dump_json()

    async def _with_filler[T](self, context: RunContext, slow: Awaitable[T]) -> T:
        """Awaits `slow`, saying a short filler first if it takes longer than FILLER_DELAY_S."""
        task = asyncio.ensure_future(slow)
        await asyncio.wait({task}, timeout=FILLER_DELAY_S)
        # Don't start a new filler while the last one is still playing.
        if not task.done() and (self._filler is None or self._filler.done()):
            # Kept out of the chat history: the LLM should answer, not continue the filler.
            self._filler = context.session.say(random.choice(FILLERS), add_to_chat_ctx=False)
            await asyncio.sleep(MIN_LOOKUP_AFTER_FILLER_S)
        return await task

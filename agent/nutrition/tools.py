import asyncio
import random
from dataclasses import asdict

from livekit.agents import RunContext, function_tool, llm
from livekit.agents.voice import SpeechHandle

from .diary import DailyIntake, Diary
from .nutrition import Macros, Nutrition

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
up every food they name, pick the match that fits each, and call prepare_food_log once per food in
the same turn, before you ask anything: the user sees the pending foods on screen while you read
them back as one short list with the total calories and ask whether to log them. One clear yes
saves them all with confirm_food_log; on no, call cancel_food_log; to drop one food ("but no
milk"), cancel it by name, then confirm the rest; if they change a food or amount, prepare it
again. For a countable food (a banana, a burrito) assume a normal one and say so; otherwise ask
how much. If USDA doesn't have it, prepare your own estimate with prepare_estimated_food_log, also
before asking, and say it's an estimate. For anything about what they've eaten or have left today, call
get_daily_totals first.

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
FILLER_DELAY = 0.6
# After a filler, answer no sooner than this, so it sounds like Sarjy actually looked it up.
MIN_LOOKUP_AFTER_FILLER = 1.2
FILLERS = [
    "Hmm, let me check.",
    "Oh, one sec.",
    "Let me pull that up.",
    "Good question, one sec.",
    "Hang on, checking.",
    "Let me see.",
    "Uh, give me a sec.",
    "Okay, looking it up.",
]


class NutritionToolset(llm.Toolset):
    """The nutrition tools the LLM can call, plus the instructions for using them."""

    instructions = INSTRUCTIONS

    def __init__(self, nutrition: Nutrition, diary: Diary):
        super().__init__(id="nutrition")
        self.nutrition = nutrition
        self.diary = diary
        self._filler: SpeechHandle | None = None

    @function_tool
    async def lookup_nutrition(self, context: RunContext, food: str, grams: float) -> dict:
        """Looks up calories and macros for an amount of food in USDA's database.

        Args:
            food: A generic food name, e.g. "chicken breast cooked" or "white rice cooked".
            grams: The amount in grams.
        """
        lookup = asyncio.ensure_future(self.nutrition.lookup(food, grams))
        done, _ = await asyncio.wait({lookup}, timeout=FILLER_DELAY)
        # Don't start a new filler while the last one is still playing.
        if not done and (self._filler is None or self._filler.done()):
            # Kept out of the chat history: the LLM should answer, not continue the filler.
            self._filler = context.session.say(random.choice(FILLERS), add_to_chat_ctx=False)
            await asyncio.sleep(MIN_LOOKUP_AFTER_FILLER)
        return await lookup

    @function_tool
    async def prepare_food_log(self, match_id: int, grams: float, name: str) -> dict:
        """Proposes logging one food the user ate, using a match from lookup_nutrition; call it
        once per food, right after the lookups, before asking whether to log them. Nothing is
        saved until confirm_food_log; the user sees the foods as pending.

        Args:
            match_id: The id of the lookup_nutrition match that fits what the user ate.
            grams: The amount the user ate, in grams.
            name: The food as the user would say it, shown on screen, in sentence case, e.g.
                "Banana", "Big Mac", "Beef burrito"; never USDA's description.
        """
        intake = await self.diary.propose(match_id, grams, name)
        if intake is None:
            return {
                "status": "unknown_food",
                "next": "Call lookup_nutrition, then use one of its ids.",
            }
        return {"status": "pending", "pending": asdict(intake)["pending"]}

    @function_tool
    async def prepare_estimated_food_log(
        self,
        food: str,
        grams: float,
        calories: float,
        protein_g: float,
        carbs_g: float,
        fat_g: float,
    ) -> dict:
        """Proposes logging a food USDA doesn't have, with your own estimate for that amount.
        Saved only after confirm_food_log, and marked as an estimate.

        Args:
            food: What the user ate, shown on screen, in sentence case, e.g. "Chicken kabsa".
            grams: The amount the user ate, in grams.
            calories: Your estimate for that amount.
            protein_g: Your estimate for that amount.
            carbs_g: Your estimate for that amount.
            fat_g: Your estimate for that amount.
        """
        macros = Macros(calories, protein_g, carbs_g, fat_g)
        intake = await self.diary.propose_estimate(food, grams, macros)
        return {"status": "pending", "pending": asdict(intake)["pending"]}

    @function_tool
    async def confirm_food_log(self) -> dict:
        """Saves all pending foods. Call only after the user clearly says yes to logging them."""
        intake = await self.diary.confirm()
        if intake is None:
            return {"status": "nothing_pending"}
        return {"status": "saved", **_day(intake)}

    @function_tool
    async def cancel_food_log(self, food: str = "") -> dict:
        """Drops pending foods the user doesn't want logged.

        Args:
            food: The name you gave the food in prepare_food_log, to drop just that one; empty
                to drop all pending foods.
        """
        intake = await self.diary.cancel(food or None)
        if intake is None:
            pending = self.diary.intake().pending
            return {"status": "not_found", "pending": [portion.name for portion in pending]}
        return {"status": "cancelled", "pending": [portion.name for portion in intake.pending]}

    @function_tool
    async def get_daily_totals(self) -> dict:
        """Today's logged foods, totals, demo targets and what's remaining."""
        return _day(self.diary.intake())


def _day(intake: DailyIntake) -> dict:
    return {
        "foods": [portion.usda_description or portion.name for portion in intake.eaten],
        "totals": asdict(intake.totals),
        "targets": asdict(intake.targets),
        "remaining": asdict(intake.remaining),
    }

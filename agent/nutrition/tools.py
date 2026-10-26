import asyncio
import random

from livekit.agents import RunContext, function_tool, llm
from livekit.agents.voice import SpeechHandle

from .nutrition import Nutrition

INSTRUCTIONS = """
- Nutrition: look up calories and macros of foods (from USDA).
For nutrition questions, call lookup_nutrition and mention which USDA food you used.
If the lookup is unavailable or the food isn't found, say so, then give your own estimate and
clearly call it an estimate. If the user doesn't say how much, ask; if they use a unit other
than grams, convert it and state your assumption."""

# Said only when a lookup is slow, so quick answers come without filler.
FILLER_DELAY = 0.6
FILLERS = ["Let me look that up.", "One sec.", "Checking the numbers.", "Let me see."]


class NutritionTools(llm.Toolset):
    """The nutrition tools the LLM can call, plus the instructions for using them."""

    instructions = INSTRUCTIONS

    def __init__(self, nutrition: Nutrition):
        super().__init__(id="nutrition")
        self.nutrition = nutrition
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
        return await lookup

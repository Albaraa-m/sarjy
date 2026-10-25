from livekit.agents import RunContext, function_tool, llm

from .nutrition import Nutrition

INSTRUCTIONS = """
- Nutrition: look up calories and macros of foods (from USDA).
For nutrition questions, call lookup_nutrition and mention which USDA food you used.
If the lookup is unavailable or the food isn't found, say so, then give your own estimate and
clearly call it an estimate. If the user doesn't say how much, ask; if they use a unit other
than grams, convert it and state your assumption."""


class NutritionTools(llm.Toolset):
    """The nutrition tools the LLM can call, plus the instructions for using them."""

    instructions = INSTRUCTIONS

    def __init__(self, nutrition: Nutrition):
        super().__init__(id="nutrition")
        self.nutrition = nutrition

    @function_tool
    async def lookup_nutrition(self, context: RunContext, food: str, grams: float) -> dict:
        """Looks up calories and macros for an amount of food in USDA's database.

        Args:
            food: A generic food name, e.g. "chicken breast cooked" or "white rice cooked".
            grams: The amount in grams.
        """
        context.session.say("Let me check USDA's database.")
        return await self.nutrition.lookup(food, grams)

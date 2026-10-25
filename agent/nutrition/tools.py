from typing import Literal

from livekit.agents import RunContext, ToolError, function_tool, llm

from .nutrition import Nutrition

INSTRUCTIONS = """
- Nutrition: look up calories and macros of foods (from USDA) and keep a daily food log.
For nutrition questions, call lookup_nutrition and mention which USDA food you used.
If the lookup is unavailable or the food isn't found, say so, then give your own estimate and
clearly call it an estimate. If the user doesn't say how much they ate, ask; if they use a unit
other than grams, convert it and state your assumption. Only log food when the user asks."""


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

    @function_tool
    async def log_food(
        self,
        food: str,
        grams: float,
        calories: float,
        protein_g: float,
        carbs_g: float,
        fat_g: float,
        source: Literal["usda", "estimate"],
    ) -> dict:
        """Records food the user ate today and returns today's totals.

        Args:
            food: What the user ate.
            grams: The amount in grams.
            calories: Calories for that amount.
            protein_g: Protein in grams for that amount.
            carbs_g: Carbohydrates in grams for that amount.
            fat_g: Fat in grams for that amount.
            source: The "source" returned by lookup_nutrition, or "estimate" if you estimated.
        """
        try:
            return await self.nutrition.log(
                food, grams, calories, protein_g, carbs_g, fat_g, source
            )
        except Exception as error:
            raise ToolError("Couldn't save the food log, please try again later.") from error

    @function_tool
    async def get_daily_totals(self) -> dict:
        """Returns today's calorie and macro totals and the foods logged so far."""
        return await self.nutrition.today()

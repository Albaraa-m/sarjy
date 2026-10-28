from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict


class Macros(BaseModel):
    model_config = ConfigDict(frozen=True)

    calories: float
    protein_g: float
    carbs_g: float
    fat_g: float

    def scaled(self, grams: float) -> Macros:
        """Scales macros given per 100 g to `grams`, rounded to 0.1."""
        factor = grams / 100
        return Macros(
            calories=round(self.calories * factor, 1),
            protein_g=round(self.protein_g * factor, 1),
            carbs_g=round(self.carbs_g * factor, 1),
            fat_g=round(self.fat_g * factor, 1),
        )

    def __add__(self, other: Macros) -> Macros:
        return Macros(
            calories=round(self.calories + other.calories, 1),
            protein_g=round(self.protein_g + other.protein_g, 1),
            carbs_g=round(self.carbs_g + other.carbs_g, 1),
            fat_g=round(self.fat_g + other.fat_g, 1),
        )

    def remaining_after(self, eaten: Macros) -> Macros:
        """What's left of these targets after `eaten`, never below zero."""
        return Macros(
            calories=max(round(self.calories - eaten.calories, 1), 0),
            protein_g=max(round(self.protein_g - eaten.protein_g, 1), 0),
            carbs_g=max(round(self.carbs_g - eaten.carbs_g, 1), 0),
            fat_g=max(round(self.fat_g - eaten.fat_g, 1), 0),
        )


NO_MACROS = Macros(calories=0, protein_g=0, carbs_g=0, fat_g=0)


class UsdaFood(BaseModel):
    model_config = ConfigDict(frozen=True)

    fdc_id: int
    description: str
    per_100g: Macros

    def portion(self, grams: float, name: str) -> Portion:
        return Portion(
            name=name,
            usda_description=self.description,
            grams=grams,
            macros=self.per_100g.scaled(grams),
            source="usda",
        )


class Portion(BaseModel):
    """An amount of something the user ate, with its macros for that amount."""

    model_config = ConfigDict(frozen=True)

    # What the user and the UI call it: "Banana", not USDA's "Bananas, raw".
    name: str
    usda_description: str | None
    grams: float
    macros: Macros
    source: Literal["usda", "estimate"]


class DailyIntake(BaseModel):
    """Serialized as the JSON the web "Today" panel parses (web/lib/parse-daily-intake.ts)."""

    model_config = ConfigDict(frozen=True)

    day: date
    eaten: list[Portion]
    pending: list[Portion]
    totals: Macros
    targets: Macros
    remaining: Macros

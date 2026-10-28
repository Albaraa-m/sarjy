from nutrition import Macros, UsdaFood

BANANA = Macros(calories=89, protein_g=1.09, carbs_g=22.84, fat_g=0.33)


def test_scales_macros_from_100_grams():
    assert BANANA.scaled(118) == Macros(calories=105.0, protein_g=1.3, carbs_g=27.0, fat_g=0.4)


def test_adds_macros_rounded_to_a_tenth():
    one = Macros(calories=0.1, protein_g=1.0, carbs_g=2.0, fat_g=3.0)
    two = Macros(calories=0.2, protein_g=1.05, carbs_g=0, fat_g=0)
    assert one + two == Macros(calories=0.3, protein_g=2.0, carbs_g=2.0, fat_g=3.0)


def test_remaining_never_goes_below_zero():
    targets = Macros(calories=2200, protein_g=150, carbs_g=220, fat_g=70)
    eaten = Macros(calories=2500, protein_g=40.25, carbs_g=220, fat_g=10)
    expected = Macros(calories=0, protein_g=109.8, carbs_g=0, fat_g=60)
    assert targets.remaining_after(eaten) == expected


def test_a_usda_food_portion_keeps_usdas_description():
    banana = UsdaFood(fdc_id=1, description="Bananas, raw", per_100g=BANANA)
    portion = banana.portion(118, "Banana")
    assert (portion.name, portion.usda_description, portion.source) == (
        "Banana",
        "Bananas, raw",
        "usda",
    )
    assert portion.macros == BANANA.scaled(118)

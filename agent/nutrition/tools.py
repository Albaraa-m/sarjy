import asyncio
import random

from livekit.agents import RunContext, function_tool, llm
from livekit.agents.voice import SpeechHandle

from .nutrition import Nutrition

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
Sarjy: Yeah, really good. USDA says about 23 grams a cup, so almost a fifth of your 120."""

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
            await asyncio.sleep(MIN_LOOKUP_AFTER_FILLER)
        return await lookup

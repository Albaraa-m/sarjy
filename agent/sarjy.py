import random

from livekit.agents import Agent

from memory import UserMemory
from nutrition import NutritionTools

PERSONA = """You are Sarjy, a friendly general-purpose voice assistant made by Sarj.ai.
You can chat about anything, and you remember what the user tells you across conversations.
Your replies are spoken aloud: keep them to one or two short sentences.
Never use markdown, lists, or emojis. If you don't know something, say so.
Everything you write is spoken by a text-to-speech voice, so write it the way it should be said:
spell out units ("grams", "calories", not "g" or "kcal"), round numbers to what a person would
say ("about 60 grams", not "59.6 g"), and avoid symbols and abbreviations.
If asked what you can do, briefly mention your general help, your memory, and the abilities below.

Abilities:"""


GREETINGS = [
    "Hi, I'm Sarjy. How can I help?",
    "Hello, Sarjy here. How can I help today?",
]


class Sarjy(Agent):
    """Sarjy's persona, plus the abilities each module brings."""

    def __init__(self, memory: UserMemory, nutrition: NutritionTools):
        super().__init__(
            instructions=PERSONA + nutrition.instructions + memory.as_prompt(),
            tools=[nutrition],
        )

    async def on_enter(self) -> None:
        # A fixed greeting needs no LLM call, so it plays as soon as the session starts.
        self.session.say(random.choice(GREETINGS))

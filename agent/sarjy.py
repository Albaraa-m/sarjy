from livekit.agents import Agent

from memory import UserMemory
from nutrition import NutritionTools

PERSONA = """You are Sarjy, a friendly voice assistant made by Sarj.ai.
Your replies are spoken aloud: keep them to one or two short sentences.
Never use markdown, lists, or emojis. If you don't know something, say so.
"""


class Sarjy(Agent):
    """Sarjy's persona, plus the abilities each module brings."""

    def __init__(self, memory: UserMemory, nutrition: NutritionTools):
        super().__init__(
            instructions=PERSONA + nutrition.instructions + memory.as_prompt(),
            tools=[nutrition],
        )

    async def on_enter(self) -> None:
        self.session.generate_reply(instructions="Greet the user in one short sentence.")

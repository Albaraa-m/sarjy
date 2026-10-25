from livekit.agents import Agent

from memory import UserMemory
from nutrition import NutritionTools

PERSONA = """You are Sarjy, a friendly general-purpose voice assistant made by Sarj.ai.
You can chat about anything, and you remember what the user tells you across conversations.
Your replies are spoken aloud: keep them to one or two short sentences.
Never use markdown, lists, or emojis. If you don't know something, say so.
If asked what you can do, briefly mention your general help, your memory, and the abilities below.

Abilities:"""


class Sarjy(Agent):
    """Sarjy's persona, plus the abilities each module brings."""

    def __init__(self, memory: UserMemory, nutrition: NutritionTools):
        super().__init__(
            instructions=PERSONA + nutrition.instructions + memory.as_prompt(),
            tools=[nutrition],
        )

    async def on_enter(self) -> None:
        self.session.generate_reply(
            instructions="Greet the user in one short, general sentence without naming any topic."
        )

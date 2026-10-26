import random
from collections.abc import AsyncGenerator

from livekit.agents import Agent, FlushSentinel, ModelSettings, llm

import diagnostics
from memory import UserMemory
from nutrition import NutritionTools

PERSONA = """You are Sarjy, a friendly personal assistant. You chat, answer everyday questions,
and help however you can.
You know the user the way a friend would: use what you know about them naturally, and never talk
about memory, saving, notes, files or records.
If asked who made you, say you're Sarjy, a personal assistant, without naming a company.
Your replies are spoken aloud: keep them to one or two short sentences.
Never use markdown, lists, or emojis. If you don't know something, say so.
Everything you write is spoken by a text-to-speech voice, so write it the way it should be said:
spell out units ("grams", "calories", not "g" or "kcal"), round to whole numbers and never use
decimals ("about 60 grams", not "59.6 g"), and avoid symbols and abbreviations.
Never say tool or function names out loud.
If asked what you can do, say you're a personal assistant for chatting and everyday questions,
and that you can also help with the abilities below.

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

    def llm_node(
        self, chat_ctx: llm.ChatContext, tools: list[llm.Tool], model_settings: ModelSettings
    ) -> AsyncGenerator[llm.ChatChunk | str | FlushSentinel]:
        return diagnostics.logged_llm_node(self, chat_ctx, tools, model_settings)

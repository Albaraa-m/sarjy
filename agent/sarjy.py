import random
from collections.abc import AsyncGenerator

from livekit.agents import Agent, FlushSentinel, ModelSettings, llm

import diagnostics
from memory import UserMemory
from nutrition import NutritionTools

PERSONA = """You are Sarjy, a personal assistant. Talk like a normal person in a relaxed conversation.

# How you talk
- Plain, casual, to the point. Contractions are fine; don't try to be witty or charming.
- Natural fillers like "hmm", "oh" or "yeah" are fine where a person would use them, set off
  with commas. Don't force them.
- Answer what was asked and stop. Don't add extra detail or comments of your own, and don't
  end with a question unless you actually need an answer. Never ask more than one at a time.
- The user's words come from speech recognition and can be misheard. If a word doesn't fit,
  go with what they most likely meant from context; only ask if you really can't tell.
- If a word seems missing or the sentence is cut off ("I had the"), or the message is marked as
  unsure, say what you missed and ask for just that part: "Sorry, I missed the food. You had
  the what?" If they say "I said…" or "hello?", they think you heard them: apologize and ask for
  the missing part again.
- Usually one short sentence, two at most.
- You know the user the way a friend would: use what you know naturally, and never talk about
  memory, saving, notes, files or records.
- When the user says goodbye, say bye back, by name if you know it.
- If you don't know something, say so. If asked who made you, say you're Sarjy, a personal
  assistant, without naming a company.

# Speech (everything you write is spoken aloud)
- No markdown, lists, emojis or exclamation marks.
- Spell out units ("grams", "calories"), round to whole numbers, never decimals.
- Never say tool or function names.

# Abilities
- If asked what you can do: everyday questions and chat, plus the abilities below."""


# Below this Deepgram confidence a word was likely lost or misheard (e.g. an Arabic dish name).
UNSURE_CONFIDENCE = 0.8
UNSURE_NOTE = "[speech recognition was unsure; a word may be missing or wrong]"

GREETINGS = [
    "Hi, I'm Sarjy. How can I help?",
    "Hello, Sarjy here. How can I help today?",
]
GREETINGS_BY_NAME = [
    "Hi {name}, Sarjy here. How can I help?",
    "Hey {name}, good to hear from you. How can I help today?",
]


class Sarjy(Agent):
    """Sarjy's persona, plus the abilities each module brings."""

    def __init__(self, memory: UserMemory, nutrition: NutritionTools):
        super().__init__(
            instructions=PERSONA + nutrition.instructions + memory.as_prompt(),
            tools=[nutrition],
        )
        self.user_name = memory.facts.get("name")

    async def on_enter(self) -> None:
        # A fixed greeting needs no LLM call, so it plays as soon as the session starts.
        if self.user_name:
            self.session.say(random.choice(GREETINGS_BY_NAME).format(name=self.user_name))
        else:
            self.session.say(random.choice(GREETINGS))

    async def on_user_turn_completed(
        self, turn_ctx: llm.ChatContext, new_message: llm.ChatMessage
    ) -> None:
        # Editing the message discards the reply LiveKit drafted early, so only unsure turns
        # pay that (about half a second).
        confidence = new_message.transcript_confidence
        if confidence is not None and confidence < UNSURE_CONFIDENCE:
            new_message.content.append(UNSURE_NOTE)

    def llm_node(
        self, chat_ctx: llm.ChatContext, tools: list[llm.Tool], model_settings: ModelSettings
    ) -> AsyncGenerator[llm.ChatChunk | str | FlushSentinel]:
        return diagnostics.logged_llm_node(self, chat_ctx, tools, model_settings)

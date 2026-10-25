import os
from typing import Literal

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    ConversationItemAddedEvent,
    JobContext,
    RunContext,
    ToolError,
    function_tool,
)
from livekit.plugins import cartesia, deepgram, groq

import nutrition
from food_log import FoodLog
from memory import UserMemory

load_dotenv()

INSTRUCTIONS = """You are Sarjy, a friendly voice assistant made by Sarj.ai.
Your replies are spoken aloud: keep them to one or two short sentences.
Never use markdown, lists, or emojis. If you don't know something, say so.

You help the user track calories and macros. For nutrition questions, call lookup_nutrition and
mention which USDA food you used.
If the lookup is unavailable or the food isn't found, say so, then give your own estimate and
clearly call it an estimate. If the user doesn't say how much they ate, ask; if they use a unit
other than grams, convert it and state your assumption. Only log food when the user asks."""

server = AgentServer()


class Sarjy(Agent):
    def __init__(self, memory: UserMemory, food_log: FoodLog):
        super().__init__(instructions=INSTRUCTIONS + memory.as_prompt())
        self.memory = memory
        self.food_log = food_log

    async def on_enter(self) -> None:
        self.session.on("conversation_item_added", self.on_conversation_item_added)
        self.session.generate_reply(instructions="Greet the user in one short sentence.")

    def on_conversation_item_added(self, event: ConversationItemAddedEvent) -> None:
        # Fires for spoken and typed messages (on_user_turn_completed misses typed ones).
        message = event.item
        if message.type == "message" and message.role == "user" and message.text_content:
            self.memory.remember_in_background(message.text_content)

    @function_tool
    async def lookup_nutrition(self, context: RunContext, food: str, grams: float) -> dict:
        """Looks up calories and macros for an amount of food in USDA's database.

        Args:
            food: A generic food name, e.g. "chicken breast cooked" or "white rice cooked".
            grams: The amount in grams.
        """
        context.session.say("Let me check USDA's database.")
        return await nutrition.lookup(food, grams)

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
            await self.food_log.add(food, grams, calories, protein_g, carbs_g, fat_g, source)
            return await self.food_log.today()
        except Exception as error:
            raise ToolError("Couldn't save the food log, please try again later.") from error

    @function_tool
    async def get_daily_totals(self) -> dict:
        """Returns today's calorie and macro totals and the foods logged so far."""
        return await self.food_log.today()


async def get_user_id(ctx: JobContext) -> str:
    participant = await ctx.wait_for_participant()
    return participant.identity


@server.rtc_session(agent_name="sarjy")
async def entrypoint(ctx: JobContext):
    user_id = await get_user_id(ctx)
    memory = await UserMemory.load(user_id)
    # Let the last turns finish saving before the job exits.
    ctx.add_shutdown_callback(memory.wait_for_pending)

    # VAD (Silero) and turn detection (LiveKit turn detector) use framework defaults.
    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=groq.LLM(model="openai/gpt-oss-120b", reasoning_effort="low"),
        tts=cartesia.TTS(model="sonic-3", voice=os.environ["CARTESIA_VOICE_ID"]),
    )
    await session.start(agent=Sarjy(memory, FoodLog(user_id)), room=ctx.room)

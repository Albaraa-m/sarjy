import logging

from dotenv import load_dotenv
from livekit.agents import AgentServer, AgentSession, JobContext, llm
from livekit.plugins import cartesia, deepgram, groq, openai

import diagnostics
from memory import UserMemory
from nutrition import DaySummary, FoodLog, Nutrition, NutritionTools
from sarjy import Sarjy

load_dotenv()

logger = logging.getLogger("sarjy")

server = AgentServer()

# Cartesia's "Layan" voice.
VOICE_ID = "64a941ac-07ac-462c-a81c-008e353dd83e"
# Says "Sarjy" the Arabic way (سرجي); the transcript keeps the English spelling.
PRONUNCIATION_DICT_ID = "pdict_PoUFShWfoiSB8iYAxWrE42"


async def get_user_id(ctx: JobContext) -> str:
    participant = await ctx.wait_for_participant()
    return participant.identity


@server.rtc_session(agent_name="sarjy")
async def entrypoint(ctx: JobContext):
    user_id = await get_user_id(ctx)
    logger.info("session started for user %s", user_id)
    memory = await UserMemory.load(user_id)

    async def show_food_log(summary: DaySummary) -> None:
        # The web "Today" panel renders this attribute; a browser that (re)joins gets the latest.
        await ctx.room.local_participant.set_attributes({"nutrition": summary.to_json()})

    nutrition = Nutrition()
    food_log = await FoodLog.load(user_id, nutrition, on_change=show_food_log)

    # VAD (Silero) and turn detection (LiveKit turn detector) use framework defaults.
    session = AgentSession(
        stt=deepgram.STT(model="nova-3", keyterm=["Sarjy"]),
        # Qwen on Cerebras has the rate limits a live demo needs; if it fails or is rate limited,
        # the same request goes to gpt-oss on Groq. Low (not "none") reasoning: with thinking fully
        # off, Qwen on Cerebras often stops after a word or two.
        llm=llm.FallbackAdapter(
            [
                openai.LLM.with_cerebras(model="qwen-3.8-27b", reasoning_effort="low"),
                groq.LLM(model="openai/gpt-oss-120b", reasoning_effort="low"),
            ]
        ),
        tts=cartesia.TTS(
            model="sonic-3.6",
            voice=VOICE_ID,
            pronunciation_dict_id=PRONUNCIATION_DICT_ID,
        ),
        # Wait a bit longer than the 0.5 s default before ending the user's turn, so pauses
        # mid-sentence ("I ate rice... and chicken") don't make Sarjy talk over the user.
        turn_handling={"endpointing": {"min_delay": 0.8}},
        # Logging a meal takes lookups, then prepares, then the read-back; the default of 3 steps
        # cut a three-food breakfast short.
        max_tool_steps=5,
    )
    memory.listen(session)
    ctx.add_shutdown_callback(memory.remember_rest)
    diagnostics.watch(session)
    await session.start(agent=Sarjy(memory, NutritionTools(nutrition, food_log)), room=ctx.room)
    await show_food_log(food_log.summary())

import logging

from dotenv import load_dotenv
from livekit.agents import AgentServer, AgentSession, JobContext, llm
from livekit.plugins import cartesia, deepgram, groq, openai

import diagnostics
from memory import UserMemory
from nutrition.diary import Diary
from nutrition.models import DailyIntake
from nutrition.tools import NutritionToolset
from sarjy import Sarjy
from settings import settings

# LiveKit's CLI reads its LIVEKIT_* credentials from the environment.
load_dotenv()

logger = logging.getLogger("sarjy")

server = AgentServer()

LAYAN_VOICE_ID = "64a941ac-07ac-462c-a81c-008e353dd83e"
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

    async def show_intake(intake: DailyIntake) -> None:
        # The web "Today" panel renders this attribute; a browser that (re)joins gets the latest.
        await ctx.room.local_participant.set_attributes({"nutrition": intake.model_dump_json()})

    diary = await Diary.load(user_id, on_change=show_intake)
    # Before the voice session starts, so the panel fills in as Sarjy joins, not seconds later.
    await show_intake(diary.intake())

    # VAD (Silero) and turn detection (LiveKit turn detector) use framework defaults.
    session = AgentSession(
        stt=deepgram.STT(
            model="nova-3",
            keyterm=["Sarjy"],
            api_key=settings.deepgram_api_key.get_secret_value(),
        ),
        # Qwen on Cerebras has the rate limits a live demo needs; if it fails or is rate limited,
        # the same request goes to gpt-oss on Groq. Low (not "none") reasoning: with thinking fully
        # off, Qwen on Cerebras often stops after a word or two.
        llm=llm.FallbackAdapter(
            [
                openai.LLM.with_cerebras(
                    model="qwen-3.8-27b",
                    reasoning_effort="low",
                    api_key=settings.cerebras_api_key.get_secret_value(),
                ),
                groq.LLM(
                    model="openai/gpt-oss-120b",
                    reasoning_effort="low",
                    api_key=settings.groq_api_key.get_secret_value(),
                ),
            ]
        ),
        tts=cartesia.TTS(
            model="sonic-3.6",
            voice=LAYAN_VOICE_ID,
            pronunciation_dict_id=PRONUNCIATION_DICT_ID,
            api_key=settings.cartesia_api_key.get_secret_value(),
        ),
        # Wait a bit longer than the 0.5 s default before ending the user's turn, so pauses
        # mid-sentence ("I ate rice... and chicken") don't make Sarjy talk over the user.
        turn_handling={"endpointing": {"min_delay": 0.8}},
        # Logging a meal takes lookups, then proposals, then the read-back; the default of 3 steps
        # cut a three-food breakfast short.
        max_tool_steps=5,
    )
    memory.listen(session)
    ctx.add_shutdown_callback(memory.remember_rest)
    diagnostics.watch(session)
    await session.start(agent=Sarjy(memory, NutritionToolset(diary)), room=ctx.room)

import logging
import os

from dotenv import load_dotenv
from livekit.agents import AgentServer, AgentSession, JobContext, llm
from livekit.plugins import cartesia, deepgram, groq, openai

import diagnostics
from memory import UserMemory
from nutrition import Nutrition, NutritionTools
from sarjy import Sarjy

load_dotenv()

logger = logging.getLogger("sarjy")

server = AgentServer()


async def get_user_id(ctx: JobContext) -> str:
    participant = await ctx.wait_for_participant()
    return participant.identity


@server.rtc_session(agent_name="sarjy")
async def entrypoint(ctx: JobContext):
    user_id = await get_user_id(ctx)
    logger.info("session started for user %s", user_id)
    memory = await UserMemory.load(user_id)
    # Let the last turns finish saving before the job exits.
    ctx.add_shutdown_callback(memory.wait_for_pending)

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
        tts=cartesia.TTS(model="sonic-3.6", voice=os.environ["CARTESIA_VOICE_ID"]),
        # Wait a bit longer than the 0.5 s default before ending the user's turn, so pauses
        # mid-sentence ("I ate rice... and chicken") don't make Sarjy talk over the user.
        turn_handling={"endpointing": {"min_delay": 0.8}},
    )
    memory.listen(session)
    diagnostics.watch(session)
    await session.start(agent=Sarjy(memory, NutritionTools(Nutrition())), room=ctx.room)

import os

from dotenv import load_dotenv
from livekit.agents import Agent, AgentServer, AgentSession, JobContext
from livekit.plugins import cartesia, deepgram, groq

load_dotenv()

INSTRUCTIONS = """You are Sarjy, a friendly voice assistant made by Sarj.ai.
Your replies are spoken aloud: keep them to one or two short sentences.
Never use markdown, lists, or emojis. If you don't know something, say so."""

server = AgentServer()


@server.rtc_session(agent_name="sarjy")
async def entrypoint(ctx: JobContext):
    # Defaults to Silero for VAD and LiveKit turn detector.
    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=groq.LLM(model="openai/gpt-oss-120b", reasoning_effort="low"),
        tts=cartesia.TTS(model="sonic-3", voice=os.environ["CARTESIA_VOICE_ID"]),
    )
    await session.start(agent=Agent(instructions=INSTRUCTIONS), room=ctx.room)
    session.generate_reply(instructions="Greet the user in one short sentence.")

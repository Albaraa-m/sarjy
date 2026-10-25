import os

from dotenv import load_dotenv
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    ConversationItemAddedEvent,
    JobContext,
)
from livekit.plugins import cartesia, deepgram, groq

from memory import UserMemory

load_dotenv()

INSTRUCTIONS = """You are Sarjy, a friendly voice assistant made by Sarj.ai.
Your replies are spoken aloud: keep them to one or two short sentences.
Never use markdown, lists, or emojis. If you don't know something, say so."""

server = AgentServer()


class Sarjy(Agent):
    def __init__(self, memory: UserMemory):
        super().__init__(instructions=INSTRUCTIONS + memory.as_prompt())
        self.memory = memory

    async def on_enter(self) -> None:
        self.session.on("conversation_item_added", self.on_conversation_item_added)
        self.session.generate_reply(instructions="Greet the user in one short sentence.")

    def on_conversation_item_added(self, event: ConversationItemAddedEvent) -> None:
        # Fires for spoken and typed messages (on_user_turn_completed misses typed ones).
        message = event.item
        if message.type == "message" and message.role == "user" and message.text_content:
            self.memory.remember_in_background(message.text_content)


async def get_user_id(ctx: JobContext) -> str:
    participant = await ctx.wait_for_participant()
    return participant.identity


@server.rtc_session(agent_name="sarjy")
async def entrypoint(ctx: JobContext):
    memory = await UserMemory.load(await get_user_id(ctx))
    # Let the last turns finish saving before the job exits.
    ctx.add_shutdown_callback(memory.wait_for_pending)

    # VAD (Silero) and turn detection (LiveKit turn detector) use framework defaults.
    session = AgentSession(
        stt=deepgram.STT(model="nova-3"),
        llm=groq.LLM(model="openai/gpt-oss-120b", reasoning_effort="low"),
        tts=cartesia.TTS(model="sonic-3", voice=os.environ["CARTESIA_VOICE_ID"]),
    )
    await session.start(agent=Sarjy(memory), room=ctx.room)

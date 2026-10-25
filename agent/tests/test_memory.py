import os
import uuid

import asyncpg
import pytest
from livekit.agents import AgentSession
from livekit.plugins import groq

from agent import Sarjy
from memory import UserMemory


def make_llm() -> groq.LLM:
    return groq.LLM(model="openai/gpt-oss-120b", reasoning_effort="low")


@pytest.fixture
async def user_id():
    user_id = f"test-{uuid.uuid4()}"
    yield user_id
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        await conn.execute("delete from memories where user_id = $1", user_id)
    finally:
        await conn.close()


async def chat(user_id: str, text: str):
    """Runs one text turn in a new session, the way a returning user would start a call."""
    memory = await UserMemory.load(user_id)
    async with AgentSession(llm=make_llm()) as session:
        await session.start(Sarjy(memory))
        result = await session.run(user_input=text)
    await memory.wait_for_pending()
    return result, memory


async def test_remembers_facts_across_sessions(user_id):
    _, memory = await chat(user_id, "My favorite color is teal.")
    assert "teal" in memory.facts.values()

    result, _ = await chat(user_id, "What's my favorite color?")
    reply = result.expect.next_event().is_message(role="assistant").event().item
    assert "teal" in (reply.text_content or "").lower()

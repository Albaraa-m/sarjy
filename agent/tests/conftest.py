import os
import uuid

import asyncpg
import pytest
from dotenv import load_dotenv
from livekit.plugins import groq

load_dotenv()


@pytest.fixture
def llm() -> groq.LLM:
    return groq.LLM(model="openai/gpt-oss-120b", reasoning_effort="low")


@pytest.fixture
async def user_id():
    # A fresh user per test, deleted afterwards, so tests never share state.
    user_id = f"test-{uuid.uuid4()}"
    yield user_id
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        await conn.execute("delete from memories where user_id = $1", user_id)
        await conn.execute("delete from food_log where user_id = $1", user_id)
    finally:
        await conn.close()

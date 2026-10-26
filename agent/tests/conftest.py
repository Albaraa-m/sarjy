import os
import uuid

import asyncpg
import pytest
from dotenv import load_dotenv
from livekit.plugins import openai

load_dotenv()


@pytest.fixture
def llm() -> openai.LLM:
    return openai.LLM.with_cerebras(model="qwen-3.8-27b", reasoning_effort="none")


@pytest.fixture
async def user_id():
    # A fresh user per test, deleted afterwards, so tests never share state.
    user_id = f"test-{uuid.uuid4()}"
    yield user_id
    conn = await asyncpg.connect(os.environ["DATABASE_URL"])
    try:
        await conn.execute("delete from memories where user_id = $1", user_id)
    finally:
        await conn.close()

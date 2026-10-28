import uuid

import pytest
from livekit.plugins import openai

import database
from nutrition.diary import Diary
from nutrition.models import DailyIntake
from nutrition.tools import NutritionToolset
from settings import settings


@pytest.fixture(autouse=True)
async def database_pool():
    # Each test runs in its own event loop, and a pool can't outlive the loop it was made in.
    yield
    await database.close()


@pytest.fixture
def llm() -> openai.LLM:
    return openai.LLM.with_cerebras(
        model="qwen-3.8-27b",
        reasoning_effort="low",
        api_key=settings.cerebras_api_key.get_secret_value(),
    )


@pytest.fixture
async def user_id():
    # A fresh user per test, deleted afterwards, so tests never share state.
    user_id = f"test-{uuid.uuid4()}"
    yield user_id
    pool = await database.pool()
    await pool.execute("delete from memories where user_id = $1", user_id)
    await pool.execute("delete from food_log where user_id = $1", user_id)


async def ignore_ui(intake: DailyIntake) -> None:
    pass


@pytest.fixture
async def nutrition_tools(user_id) -> NutritionToolset:
    return NutritionToolset(await Diary.load(user_id, on_change=ignore_ui))

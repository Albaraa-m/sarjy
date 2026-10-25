from livekit.agents import AgentSession

from agent import Sarjy
from food_log import FoodLog
from memory import UserMemory


async def test_looks_up_then_logs_food(llm, user_id):
    food_log = FoodLog(user_id)
    async with AgentSession(llm=llm) as session:
        await session.start(Sarjy(await UserMemory.load(user_id), food_log))

        result = await session.run(user_input="How much protein is in 200 grams of chicken breast?")
        result.expect.contains_function_call(name="lookup_nutrition")

        result = await session.run(user_input="Log that I ate it.")
        result.expect.contains_function_call(name="log_food")

    today = await food_log.today()
    assert len(today["entries"]) == 1
    assert today["entries"][0]["source"] == "usda"

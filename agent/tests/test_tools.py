from livekit.agents import AgentSession

from memory import UserMemory
from nutrition import Nutrition, NutritionTools
from sarjy import Sarjy


async def test_looks_up_nutrition(llm, user_id):
    async with AgentSession(llm=llm) as session:
        await session.start(Sarjy(await UserMemory.load(user_id), NutritionTools(Nutrition())))
        result = await session.run(user_input="How much protein is in 200 grams of chicken breast?")
        result.expect.contains_function_call(name="lookup_nutrition")

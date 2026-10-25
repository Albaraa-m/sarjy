from livekit.agents import AgentSession
from livekit.plugins import groq

from memory import UserMemory
from nutrition import Nutrition, NutritionTools
from sarjy import Sarjy


async def chat(llm: groq.LLM, user_id: str, text: str):
    """Runs one text turn in a new session, the way a returning user would start a call."""
    memory = await UserMemory.load(user_id)
    async with AgentSession(llm=llm) as session:
        memory.listen(session)
        await session.start(Sarjy(memory, NutritionTools(Nutrition())))
        result = await session.run(user_input=text)
    await memory.wait_for_pending()
    return result, memory


async def test_remembers_facts_across_sessions(llm, user_id):
    _, memory = await chat(llm, user_id, "My favorite color is teal.")
    assert "teal" in memory.facts.values()

    result, _ = await chat(llm, user_id, "What's my favorite color?")
    reply = result.expect.next_event().is_message(role="assistant").event().item
    assert "teal" in (reply.text_content or "").lower()

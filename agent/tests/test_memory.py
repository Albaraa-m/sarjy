from livekit.agents import AgentSession
from livekit.plugins import openai

from memory import UserMemory
from nutrition import Nutrition, NutritionTools
from sarjy import Sarjy


async def chat(llm: openai.LLM, user_id: str, text: str):
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


async def test_greeting_the_assistant_is_not_the_users_name(llm, user_id):
    # Deepgram heard "Hey, Sarjy" as "Hey, Sergei" in a live call, and it was saved as the user's name.
    _, memory = await chat(
        llm, user_id, "Hey, Sergei. Can you help me with? What do you have to offer?"
    )
    assert memory.facts == {}

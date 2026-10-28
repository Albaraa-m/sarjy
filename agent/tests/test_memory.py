from livekit.agents import AgentSession
from livekit.plugins import openai

from memory import UserMemory
from nutrition.tools import NutritionToolset
from sarjy import Sarjy


async def chat(llm: openai.LLM, user_id: str, tools: NutritionToolset, text: str):
    """Runs one text turn in a new call, then remembers it as the end of a call does."""
    memory = await UserMemory.load(user_id)
    async with AgentSession(llm=llm) as session:
        memory.listen(session)
        await session.start(Sarjy(memory, tools))
        result = await session.run(user_input=text)
    await memory.remember_rest()
    return result, memory


async def test_remembers_facts_across_sessions(llm, user_id, nutrition_tools):
    _, memory = await chat(llm, user_id, nutrition_tools, "My favorite color is teal.")
    assert "teal" in memory.facts.values()

    result, _ = await chat(llm, user_id, nutrition_tools, "What's my favorite color?")
    reply = result.expect.next_event().is_message(role="assistant").event().item
    assert "teal" in (reply.text_content or "").lower()


async def test_greeting_the_assistant_is_not_the_users_name(llm, user_id, nutrition_tools):
    # Deepgram heard "Hey, Sarjy" as "Hey, Sergei" in a live call, and it was saved as the user's name.
    _, memory = await chat(
        llm,
        user_id,
        nutrition_tools,
        "Hey, Sergei. Can you help me with? What do you have to offer?",
    )
    assert memory.facts == {}


async def test_a_changed_preference_holds_in_the_next_call(llm, user_id, nutrition_tools):
    _, memory = await chat(llm, user_id, nutrition_tools, "I don't like milk.")
    assert any("milk" in key for key in memory.facts)
    _, memory = await chat(llm, user_id, nutrition_tools, "Actually, I do like milk now.")
    assert not any("dislike" in key or "dont" in key for key in memory.facts)

    result, _ = await chat(llm, user_id, nutrition_tools, "Do I like milk?")
    reply = result.expect.next_event().is_message(role="assistant").event().item
    answer = (reply.text_content or "").lower()
    assert not any(negation in answer for negation in ["don't", "do not", "dislike", "not a fan"])

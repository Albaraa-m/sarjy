from livekit.agents import AgentSession

from memory import UserMemory
from nutrition import Nutrition, NutritionTools
from sarjy import Sarjy

MEMORY_TALK = ("memory", "saved", "on file", "my records")


async def test_knows_the_user_without_mentioning_memory(llm):
    memory = UserMemory("test-persona", {"favorite_color": "teal"})
    async with AgentSession(llm=llm) as session:
        await session.start(Sarjy(memory, NutritionTools(Nutrition())))
        replies = []
        for text in ("What's my favorite color?", "My favorite food is kabsa."):
            result = await session.run(user_input=text)
            reply = result.expect.next_event().is_message(role="assistant").event().item
            replies.append((reply.text_content or "").lower())

    assert "teal" in replies[0], replies[0]
    for reply in replies:
        assert not any(word in reply for word in MEMORY_TALK), reply

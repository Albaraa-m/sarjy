import pytest
from livekit.agents import AgentSession, ChatMessage
from livekit.agents.llm import ChatContext

from memory import UserMemory
from nutrition import DailyIntake, Diary, Nutrition, NutritionToolset
from nutrition.diary import today
from sarjy import UNSURE_NOTE, Sarjy

# A live call: Deepgram dropped an Arabic dish name and returned this at 67% confidence.
CUT_OFF = "And I also had the"
FOOD_TOOLS = {
    "lookup_nutrition",
    "propose_portion",
    "propose_estimated_portion",
    "confirm_portions",
}


async def ignore_ui(intake: DailyIntake) -> None:
    pass


def sarjy() -> Sarjy:
    nutrition = Nutrition()
    diary = Diary("test-unsure", nutrition, ignore_ui, today(), [])
    return Sarjy(UserMemory("test-unsure", {}), NutritionToolset(nutrition, diary))


@pytest.mark.parametrize(("confidence", "noted"), [(0.67, True), (0.98, False), (None, False)])
async def test_only_unsure_transcripts_get_the_note(confidence, noted):
    message = ChatMessage(role="user", content=[CUT_OFF], transcript_confidence=confidence)
    await sarjy().on_user_turn_completed(ChatContext.empty(), message)
    assert (UNSURE_NOTE in message.content) == noted


async def test_asks_for_the_missing_word_instead_of_guessing(llm):
    async with AgentSession(llm=llm) as session:
        await session.start(sarjy())
        result = await session.run(user_input=f"{CUT_OFF} {UNSURE_NOTE}")
    tools = {event.item.name for event in result.events if event.type == "function_call"}
    reply = " ".join(e.item.text_content or "" for e in result.events if e.type == "message")

    called_food_tools = tools & FOOD_TOOLS
    assert called_food_tools == set(), called_food_tools
    assert "?" in reply, reply

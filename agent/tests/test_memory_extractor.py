import json

from memory.changes import Fact, MemoryChanges
from memory.llm_extractor import extract_changes, parse_changes


async def remember(conversation: str, known: dict[str, str]) -> dict[str, str]:
    facts = dict(known)
    (await extract_changes(conversation, known)).apply_to(facts)
    return facts


def reply(facts: dict[str, str] | None = None, remove: list[str] | None = None) -> str:
    to_set = [{"key": key, "value": value} for key, value in (facts or {}).items()]
    return json.dumps({"set": to_set, "remove": remove or []})


def test_malformed_reply_changes_nothing():
    assert not parse_changes('{"facts": {"color": "blue"}}', known={})
    assert not parse_changes("", known={})


def test_removing_an_unknown_key_is_ignored():
    changes = parse_changes(reply(remove=["dislikes_milk", "city"]), known={"city": "Riyadh"})
    assert changes == MemoryChanges(set=[], remove=["city"])


def test_too_many_changes_change_nothing():
    known = {f"fact_{i}": "x" for i in range(8)}
    assert not parse_changes(reply(facts={"a": "1", "b": "2", "c": "3"}, remove=list(known)), known)


def test_sentence_saved_as_a_name_is_dropped():
    changes = parse_changes(reply(facts={"name": "can you help me with", "city": "Riyadh"}), {})
    assert changes.set == [Fact(key="city", value="Riyadh")]


async def test_changing_a_preference_replaces_the_old_one():
    facts = await remember("User: Actually, I do like milk now.", known={"dislikes_milk": "yes"})
    assert "dislikes_milk" not in facts
    assert any("milk" in key for key in facts)


async def test_updating_a_fact_reuses_its_key():
    facts = await remember(
        "User: My favorite color is green now.", known={"favorite_color": "blue"}
    )
    assert facts == {"favorite_color": "green"}


async def test_user_name_uses_the_name_key():
    facts = await remember("User: I'm Albaraa, by the way.", known={})
    assert facts.get("name") == "Albaraa"


async def test_greeting_the_assistant_is_not_the_users_name():
    assert await remember("User: Hey, Sergei. What can you do?", known={}) == {}


async def test_small_talk_changes_nothing():
    known = {"name": "Albaraa", "favorite_color": "blue"}
    assert await remember("User: Haha, that's funny. How's your day going?", known) == known


async def test_self_correction_keeps_the_final_value():
    conversation = """User: My favorite color is blue.
Sarjy: Blue, nice.
User: Actually, make that green."""
    assert (await remember(conversation, known={})).get("favorite_color") == "green"


async def test_correcting_a_question_does_not_change_a_favorite():
    # "Actually, uh, brown rice" once overwrote the user's favorite food.
    known = {"favorite_food": "steak"}
    conversation = """User: How many calories are in 150 grams of rice?
Sarjy: About 195 calories for 150 grams of cooked white rice.
User: Actually, uh, brown rice.
Sarjy: 150 grams of cooked brown rice has about 220 calories."""
    assert await remember(conversation, known) == known

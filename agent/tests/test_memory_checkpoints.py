from livekit.agents import AgentSession, ChatMessage, ChatRole, ConversationItemAddedEvent

from memory import UserMemory
from memory import memory as memory_module
from memory.changes import MemoryChanges
from memory.memory import CHECKPOINT_USER_TURNS


class RecordingExtractor:
    def __init__(self):
        self.conversations: list[str] = []

    async def __call__(self, conversation: str, known: dict[str, str]) -> MemoryChanges:
        self.conversations.append(conversation)
        return MemoryChanges.none()


def add_turn(session: AgentSession, role: ChatRole, text: str) -> None:
    message = ChatMessage(role=role, content=[text])
    session.emit("conversation_item_added", ConversationItemAddedEvent(item=message))


async def test_checkpoints_never_resend_turns(monkeypatch):
    extractor = RecordingExtractor()
    monkeypatch.setattr(memory_module, "extract_changes", extractor)
    memory = UserMemory("test-checkpoints", {})
    session = AgentSession()
    memory.listen(session)

    for turn in range(CHECKPOINT_USER_TURNS + 2):
        add_turn(session, "user", f"message {turn}")
        add_turn(session, "assistant", f"reply {turn}")
    await memory.remember_rest()

    assert len(extractor.conversations) == 2
    assert extractor.conversations[0].startswith("User: message 0")
    lines = [line for conversation in extractor.conversations for line in conversation.splitlines()]
    assert sorted(lines) == sorted(
        f"{speaker}: {text} {turn}"
        for turn in range(CHECKPOINT_USER_TURNS + 2)
        for speaker, text in [("User", "message"), ("Sarjy", "reply")]
    )


async def test_a_call_without_user_turns_extracts_nothing(monkeypatch):
    extractor = RecordingExtractor()
    monkeypatch.setattr(memory_module, "extract_changes", extractor)
    memory = UserMemory("test-checkpoints", {})
    session = AgentSession()
    memory.listen(session)

    add_turn(session, "assistant", "Hi, I'm Sarjy. How can I help?")
    await memory.remember_rest()

    assert extractor.conversations == []

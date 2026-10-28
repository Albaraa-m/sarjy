import logging
from collections.abc import AsyncGenerator

from livekit.agents import (
    Agent,
    AgentFalseInterruptionEvent,
    AgentSession,
    ConversationItemAddedEvent,
    ErrorEvent,
    FlushSentinel,
    ModelSettings,
    llm,
)

logger = logging.getLogger("sarjy.diagnostics")


# Per reply, "llm generated" vs "spoken" tells whether the LLM, the TTS or LiveKit lost words.
def watch(session: AgentSession) -> None:
    session.on("conversation_item_added", _log_spoken)
    session.on("error", _log_error)
    session.on("agent_false_interruption", _log_false_interruption)


async def logged_llm_node(
    agent: Agent, chat_ctx: llm.ChatContext, tools: list[llm.Tool], model_settings: ModelSettings
) -> AsyncGenerator[llm.ChatChunk | str | FlushSentinel]:
    """The default LLM step, plus a log of everything the LLM generated for the reply."""
    generated = []
    try:
        async for chunk in Agent.default.llm_node(agent, chat_ctx, tools, model_settings):
            if isinstance(chunk, str):
                generated.append(chunk)
            elif isinstance(chunk, llm.ChatChunk) and chunk.delta and chunk.delta.content:
                generated.append(chunk.delta.content)
            yield chunk
    finally:
        if generated:
            logger.info("llm generated: %s", "".join(generated))


def _log_spoken(event: ConversationItemAddedEvent) -> None:
    message = event.item
    if message.type == "message" and message.role == "assistant":
        logger.info("spoken (interrupted=%s): %s", message.interrupted, message.text_content)


def _log_error(event: ErrorEvent) -> None:
    logger.warning("error from %s: %s", type(event.source).__name__, event.error)


def _log_false_interruption(event: AgentFalseInterruptionEvent) -> None:
    logger.info("false interruption (resumed=%s)", event.resumed)

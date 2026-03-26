"""Compatibility facade for chat service APIs.

This module keeps legacy import paths stable while the implementation
is split into smaller modules for maintainability.
"""

from app.ai.chat_models import ChatRequest, ChatResponse
from app.ai.chat_runtime import (
    AgentName,
    AGENT_CONFIG,
    DEFAULT_PROMPT_KEY,
    PROMPT_PRESETS,
    get_active_model_name,
    get_chat_runtime_settings,
    list_prompt_presets,
    resolve_system_prompt,
)
from app.ai.chat_engine import chat_service

__all__ = [
    "AgentName",
    "AGENT_CONFIG",
    "DEFAULT_PROMPT_KEY",
    "PROMPT_PRESETS",
    "ChatRequest",
    "ChatResponse",
    "chat_service",
    "get_active_model_name",
    "get_chat_runtime_settings",
    "list_prompt_presets",
    "resolve_system_prompt",
]

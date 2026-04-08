from typing import Annotated, Literal, List, Dict, Any

from pydantic import BaseModel
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

from app.ai.chat_runtime import AgentName, DEFAULT_PROMPT_KEY


class State(TypedDict):
    messages: Annotated[list, add_messages]
    selected_agent: AgentName
    intent: str
    routing_reason: str
    resolved_system_prompt: str
    force_agent: AgentName | None


class ChatRequest(BaseModel):
    system_prompt: str = ""
    prompt_key: str = DEFAULT_PROMPT_KEY
    rag_k: Literal[3, 4, 5] = 4
    strict_mode: bool = False
    user_input: str
    thread_id: str = "default"
    user_id: str | None = None
    is_admin: bool = False
    force_agent: AgentName | None = None


class ChatResponse(BaseModel):
    response: str
    tool_calls: List[Dict[str, Any]] = []
    agent: AgentName = "code_tutor"
    intent: str = "general_tutoring"
    routing_reason: str = "默认路由"

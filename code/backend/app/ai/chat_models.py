import operator
from typing import Annotated, Literal, List, Dict, Any

from pydantic import BaseModel, Field
from typing_extensions import TypedDict
from langgraph.graph.message import add_messages

from app.ai.chat_runtime import AgentName, DEFAULT_PROMPT_KEY


class State(TypedDict):
    """LangGraph 协作态：主管派发 next_agent，专员回写 messages，全程累积 intermediate_steps。"""

    messages: Annotated[list, add_messages]
    next_agent: str
    task_breakdown: str
    intermediate_steps: Annotated[list[str], operator.add]
    selected_agent: AgentName
    intent: str
    routing_reason: str
    resolved_system_prompt: str
    force_agent: AgentName | None
    force_agent_consumed: bool
    active_tools: list[str] | None
    max_tokens: int | None
    temperature: float | None
    top_p: float | None
    top_k: int | None
    supervisor_entries: int
    supervisor_fallback_streak: int
    strict_mode: bool
    collaboration_last_worker: str
    rag_user_id: str | None
    rag_is_admin: bool
    rag_top_k: int
    current_thread_id: str
    current_file_id: str | None
    current_file_name: str
    user_memory_context: str


class SupervisorDecision(BaseModel):
    """主管 LLM 结构化输出：下一步路由。"""

    next_agent: Literal[
        "code_tutor",
        "knowledge_mentor",
        "planner",
        "analyst",
        "doc_researcher",
        "quiz_master",
        "FINISH",
    ] = Field(description="下一步执行的专员，或 FINISH 表示进入汇总")
    routing_reason: str = Field(default="", description="中文简要说明为何如此路由")
    task_breakdown: str = Field(
        default="", description="当前对用户请求的拆解要点，可多条换行"
    )


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
    active_tools: list[str] | None = None
    stream: bool = False
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    selected_text: str | None = None
    surrounding_context: str | None = None
    video_time: str | None = None
    course_module: str | None = None
    # 来自 DB 的已完成轮次，用于跨 HTTP 请求延续多轮语境（与 thread_id 对应）
    prior_turns: list[dict[str, str]] | None = None
    current_file_id: str | None = None
    file_name: str | None = None


class ChatResponse(BaseModel):
    response: str
    tool_calls: List[Dict[str, Any]] = []
    agent: AgentName = "supervisor"
    intent: str = "collaborative_supervisor"
    routing_reason: str = "主管协作编排"
    thoughts: List[str] = []
    requires_confirmation: bool = False
    pending_action_id: str | None = None

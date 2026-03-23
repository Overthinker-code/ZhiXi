from typing import Annotated, Literal, List, Dict, Any
from typing_extensions import TypedDict
import base64
import re

from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage
from langchain.tools import tool
from langgraph.types import interrupt, Command
from langchain_community.tools import DuckDuckGoSearchRun
from pydantic import BaseModel

from ..services.rag_tools import (
    query_knowledge_base,
    set_rag_request_context,
    reset_rag_request_context,
)
from ..services.behavior_analysis import behavior_service
from ..services.chat_model_factory import ChatModelFactory
from ..services.rag_service import RAGService
from app.core.config import settings

search = DuckDuckGoSearchRun()

DEFAULT_PROMPT_KEY = "tutor"
PROMPT_PRESETS: dict[str, dict[str, str]] = {
    "tutor": {
        "label": "学习辅导",
        "description": "分步骤讲解，强调理解与迁移。",
        "prompt": (
            "你是一名学习辅导助手。"
            "请优先依据给定知识片段回答，禁止编造。"
            "若信息不足，明确说明并给出最小补充建议。"
        ),
    },
    "exam": {
        "label": "考试作答",
        "description": "按考试得分点组织答案。",
        "prompt": (
            "你是一名考试辅导助手。请按“得分点”结构化回答。"
            "先给【结论】，再列要点，每点简短清晰。结论部分限制在50字内。回答总字数在200字内。"
            "仅依据知识片段作答，禁止编造。"
        ),
    },
    "concise": {
        "label": "简洁速答",
        "description": "更短更直接，适合快速确认。",
        "prompt": (
            "请用简洁风格回答：先一句话结论，再给 3-5 条关键点。"
            "不展开无关背景，保持可执行。"
        ),
    },
    "socratic": {
        "label": "苏格拉底引导",
        "description": "先用问题引导思考，再给提示。",
        "prompt": (
            "请采用苏格拉底式引导：先提出 1-2 个关键问题，"
            "再给方向性提示，最后给参考答案。"
            "内容必须基于知识片段。"
        ),
    },
}


def get_active_model_name() -> str:
    if settings.CHAT_PROVIDER.lower() == "ollama":
        return settings.OLLAMA_MODEL
    return settings.CHAT_MODEL


def list_prompt_presets() -> list[dict[str, str]]:
    return [
        {
            "key": key,
            "label": value["label"],
            "description": value["description"],
        }
        for key, value in PROMPT_PRESETS.items()
    ]


def get_chat_runtime_settings() -> dict:
    return {
        "provider": settings.CHAT_PROVIDER.lower(),
        "model": get_active_model_name(),
        "rag_k_options": [3, 4, 5],
        "rag_k_default": 4,
        "strict_mode_default": False,
        "default_prompt_key": DEFAULT_PROMPT_KEY,
        "prompt_options": list_prompt_presets(),
    }


def resolve_system_prompt(prompt_key: str, custom_prompt: str) -> str:
    preset = PROMPT_PRESETS.get(prompt_key) or PROMPT_PRESETS[DEFAULT_PROMPT_KEY]
    preset_prompt = preset["prompt"].strip()
    custom = (custom_prompt or "").strip()
    if not custom:
        return preset_prompt
    return f"{preset_prompt}\n\n补充要求：\n{custom}"


class State(TypedDict):
    messages: Annotated[list, add_messages]
    control: Literal["wait_for_human", "continue"]


@tool
def search_web(query: str) -> str:
    """Search the web and return a brief summary."""
    try:
        results = search.run(query)
        return f"搜索结果：{results}"
    except Exception as e:
        return f"搜索出错：{str(e)}"


@tool
async def analyze_student_behavior(image_base64: str) -> str:
    """Analyze student behavior from an image."""
    try:
        image_data = base64.b64decode(image_base64)
        result = await behavior_service.analyze_image(image_data)

        if result["status"] == "error":
            return f"行为分析失败：{result['error']}"

        behavior_lines = []
        for behavior in result["behaviors"]:
            confidence = round(behavior["confidence"] * 100, 1)
            behavior_lines.append(
                f"- {behavior['behavior']}（置信度：{confidence}%）：{behavior['description']}"
            )

        return (
            "学习状态分析报告：\n"
            "1. 检测到的行为：\n"
            f"{chr(10).join(behavior_lines)}\n\n"
            "2. 总体评估：\n"
            f"- 学习状态：{result['learning_status']}\n"
            f"- 状态得分：{round(result['overall_score'] * 100, 1)}分\n\n"
            "3. 建议：\n"
            f"{_generate_suggestions(result['behaviors'], result['overall_score'])}"
        )
    except Exception as e:
        return f"行为分析过程出错：{str(e)}"


def _generate_suggestions(behaviors: List[dict], overall_score: float) -> str:
    suggestions: List[str] = []

    for behavior in behaviors:
        if behavior["behavior"] == "查看手机":
            suggestions.append("建议将手机放在指定区域，减少分心")
        elif behavior["behavior"] == "睡觉":
            suggestions.append("建议适当休息后再继续学习")
        elif behavior["behavior"] == "与他人交流":
            suggestions.append("建议保持安静学习环境，避免影响他人")
        elif behavior["behavior"] == "离开座位":
            suggestions.append("建议规划学习时间，减少无关走动")

    if overall_score < -0.3:
        suggestions.append("建议调整学习状态，提高专注度")
    elif overall_score > 0.7:
        suggestions.append("当前学习状态良好，建议保持")

    if not suggestions:
        suggestions.append("保持当前学习节奏，适时休息")

    return "\n".join(f"- {s}" for s in suggestions)


tools = [search_web, query_knowledge_base, analyze_student_behavior]
rag_service = RAGService()
base_llm = ChatModelFactory.create()
llm = (
    base_llm
    if settings.CHAT_PROVIDER.lower() == "ollama"
    else base_llm.bind_tools(tools)
)


def chatbot_node(state: State):
    ai_msg = llm.invoke(state["messages"])
    return {"messages": [ai_msg]}


def summarize_tool_result(state: State):
    tool_outputs = state.get("messages", [])[-1].content
    summary_prompt = {
        "role": "user",
        "content": (
            "你从工具获得了如下信息：\n\n"
            f"{tool_outputs}\n\n"
            "请将其总结为一段简洁回复，帮助用户理解。"
        ),
    }
    summary_msg = llm.invoke([summary_prompt])
    return {"messages": [summary_msg]}


def human_interrupt_node(state: State):
    latest_ai_msg = state["messages"][-1]
    response = interrupt(
        {
            "message": latest_ai_msg.content,
            "tool_calls": getattr(latest_ai_msg, "tool_calls", []),
        }
    )
    return Command(resume=response)


builder = StateGraph(State)
builder.add_node("chatbot", chatbot_node)
builder.add_node("tools", ToolNode(tools=tools))
builder.add_node("summarize", summarize_tool_result)
builder.add_node("human_gate", human_interrupt_node)

builder.add_edge(START, "chatbot")
builder.add_conditional_edges("chatbot", tools_condition)
builder.add_edge("tools", "summarize")
builder.add_edge("summarize", "chatbot")
builder.add_edge("chatbot", "human_gate")
builder.add_conditional_edges("human_gate", lambda _: "continue", {"continue": END})

graph = builder.compile(checkpointer=MemorySaver())


class ChatRequest(BaseModel):
    system_prompt: str = ""
    prompt_key: str = DEFAULT_PROMPT_KEY
    rag_k: Literal[3, 4, 5] = 4
    strict_mode: bool = False
    user_input: str
    thread_id: str = "default"
    user_id: str | None = None
    is_admin: bool = False


class ChatResponse(BaseModel):
    response: str
    tool_calls: List[Dict[str, Any]] = []


_CITATION_RE = re.compile(r"\[citation:(\d+)\]")


def _extract_citation_ids(text: str) -> set[int]:
    return {int(m.group(1)) for m in _CITATION_RE.finditer(text or "")}


def _is_strict_answer_valid(text: str, max_citation: int) -> bool:
    ids = _extract_citation_ids(text)
    if not ids:
        return False
    return all(1 <= citation_id <= max_citation for citation_id in ids)


def _strict_reject_message() -> str:
    return (
        "抱歉，当前检索结果不足以支撑可引用回答。"
        "请改写问题并补充关键词，或先上传更相关资料。"
    )


def _chat_with_ollama_rag(request: "ChatRequest") -> "ChatResponse":
    results = rag_service.query_knowledge_base(
        query=request.user_input,
        k=request.rag_k,
        user_id=request.user_id,
        is_admin=request.is_admin,
    )

    if request.strict_mode and not results:
        return ChatResponse(response=_strict_reject_message(), tool_calls=[])

    if results:
        context_chunks = "\n\n".join(
            f"[citation:{item['citation_id']}] {item['content']}" for item in results
        )
    else:
        context_chunks = "未检索到相关知识片段。"

    prompt = (
        "请基于以下知识库片段回答用户问题。\n"
        "要求：\n"
        "1. 仅依据片段内容作答，不要编造。\n"
        "2. 在关键结论后标注 [citation:x]。\n"
        "3. 信息不足时明确说明。\n\n"
        f"知识片段：\n{context_chunks}\n\n"
        f"用户问题：{request.user_input}"
    )
    if request.strict_mode:
        prompt += (
            "\n\n严格约束："
            "\n1) 只能依据上述知识片段作答。"
            "\n2) 每个关键结论后必须标注 [citation:x]。"
            "\n3) 至少使用 1 个 citation。"
            "\n4) 若证据不足，直接说明‘知识库证据不足’。"
        )

    messages: List[Any] = []
    resolved_system_prompt = resolve_system_prompt(
        request.prompt_key, request.system_prompt
    )
    if resolved_system_prompt:
        messages.append(SystemMessage(content=resolved_system_prompt))
    messages.append({"role": "user", "content": prompt})

    ai_msg = llm.invoke(messages)
    if request.strict_mode:
        max_citation = len(results)
        first_pass = str(ai_msg.content or "")
        if not _is_strict_answer_valid(first_pass, max_citation):
            repair_prompt = (
                "请重写答案并严格遵守："
                "只依据知识片段，不得编造；"
                "每个关键结论都要带 [citation:x]；"
                "citation 编号必须在可用范围内。"
                f"\n可用 citation 范围: 1..{max_citation}"
                f"\n用户问题: {request.user_input}"
                f"\n上一次答案: {first_pass}"
            )
            repair_messages: List[Any] = []
            if resolved_system_prompt:
                repair_messages.append(SystemMessage(content=resolved_system_prompt))
            repair_messages.append({"role": "user", "content": repair_prompt})
            ai_msg = llm.invoke(repair_messages)

            repaired = str(ai_msg.content or "")
            if not _is_strict_answer_valid(repaired, max_citation):
                return ChatResponse(response=_strict_reject_message(), tool_calls=[])

    return ChatResponse(response=ai_msg.content, tool_calls=[])
def chat_service(request: ChatRequest) -> ChatResponse:
    if settings.CHAT_PROVIDER.lower() == "ollama":
        return _chat_with_ollama_rag(request)

    init_msgs = []
    resolved_system_prompt = resolve_system_prompt(
        request.prompt_key, request.system_prompt
    )
    if resolved_system_prompt:
        init_msgs.append(SystemMessage(content=resolved_system_prompt))
    init_msgs.append({"role": "user", "content": request.user_input})

    state = {"messages": init_msgs, "control": "wait_for_human"}
    thread_config = {"configurable": {"thread_id": request.thread_id}}

    token_user_id, token_is_admin = set_rag_request_context(
        request.user_id, request.is_admin
    )
    try:
        result = graph.invoke(state, config=thread_config)
        last_message = result["messages"][-1]

        return ChatResponse(
            response=last_message.content,
            tool_calls=getattr(last_message, "tool_calls", []),
        )
    finally:
        reset_rag_request_context(token_user_id, token_is_admin)

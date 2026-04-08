from typing import Any, List
import re

from langgraph.graph import StateGraph, END, START
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage

from app.core.config import settings
from app.ai.chat_models import State, ChatRequest, ChatResponse
from app.ai.chat_runtime import (
    AgentName,
    AGENT_CONFIG,
    CODE_KEYWORDS,
    PLANNER_KEYWORDS,
    ANALYST_KEYWORDS,
    resolve_system_prompt,
)
from app.ai.chat_tools import TOOLS_BY_AGENT, get_llm, message_text, collect_tool_calls
from app.services.rag_tools import set_rag_request_context, reset_rag_request_context
from app.services.rag_service import RAGService

rag_service = RAGService()


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


def _latest_user_text(messages: list) -> str:
    for message in reversed(messages):
        msg_type = getattr(message, "type", "")
        role = getattr(message, "role", "")
        if msg_type == "human" or role == "user":
            return message_text(message)
    return message_text(messages[-1]) if messages else ""


def route_intent(
    user_input: str, force_agent: AgentName | None = None
) -> tuple[AgentName, str, str]:
    if force_agent in AGENT_CONFIG:
        return force_agent, "manual_override", "根据 force_agent 参数强制路由"

    normalized = (user_input or "").strip().lower()
    if any(keyword in normalized for keyword in CODE_KEYWORDS):
        return "code_tutor", "code_error_support", "检测到代码/报错相关关键词"
    if any(keyword in normalized for keyword in PLANNER_KEYWORDS):
        return "planner", "study_plan_adjustment", "检测到学习计划/进度相关关键词"
    if any(keyword in normalized for keyword in ANALYST_KEYWORDS):
        return "analyst", "learning_status_analysis", "检测到学习行为/分析相关关键词"
    return "code_tutor", "general_tutoring", "默认分配至代码导师处理泛化学习问答"


def _build_agent_messages(state: State, agent: AgentName) -> list:
    role_prompt = AGENT_CONFIG[agent]["prompt"]
    resolved = (state.get("resolved_system_prompt") or "").strip()
    merged_system_prompt = role_prompt if not resolved else f"{resolved}\n\n{role_prompt}"
    return [SystemMessage(content=merged_system_prompt), *state["messages"]]


def _invoke_agent(state: State, agent: AgentName):
    llm = get_llm(agent, enable_tools=True)
    ai_msg = llm.invoke(_build_agent_messages(state, agent))
    return {"messages": [ai_msg]}


def router_node(state: State):
    agent, intent, reason = route_intent(
        _latest_user_text(state.get("messages", [])), state.get("force_agent")
    )
    return {
        "selected_agent": agent,
        "intent": intent,
        "routing_reason": reason,
    }


def code_tutor_node(state: State):
    return _invoke_agent(state, "code_tutor")


def planner_node(state: State):
    return _invoke_agent(state, "planner")


def analyst_node(state: State):
    return _invoke_agent(state, "analyst")


def summarize_tool_result(state: State):
    tool_outputs = message_text(state.get("messages", [])[-1])
    summary_prompt = {
        "role": "user",
        "content": (
            "你从工具获得了如下信息：\n\n"
            f"{tool_outputs}\n\n"
            "请将其总结为一段简洁回复，帮助用户理解，并给出下一步建议。"
        ),
    }
    selected_agent: AgentName = state.get("selected_agent", "code_tutor")
    llm = get_llm(selected_agent, enable_tools=False)
    summary_msg = llm.invoke([summary_prompt])
    return {"messages": [summary_msg]}


def _route_from_router(state: State):
    return state.get("selected_agent", "code_tutor")


def _route_after_summarize(state: State):
    return state.get("selected_agent", "code_tutor")


def _build_multi_agent_graph():
    builder = StateGraph(State)
    builder.add_node("router", router_node)
    builder.add_node("code_tutor", code_tutor_node)
    builder.add_node("planner", planner_node)
    builder.add_node("analyst", analyst_node)
    builder.add_node("code_tutor_tools", ToolNode(tools=TOOLS_BY_AGENT["code_tutor"]))
    builder.add_node("planner_tools", ToolNode(tools=TOOLS_BY_AGENT["planner"]))
    builder.add_node("analyst_tools", ToolNode(tools=TOOLS_BY_AGENT["analyst"]))
    builder.add_node("summarize", summarize_tool_result)

    builder.add_edge(START, "router")
    builder.add_conditional_edges(
        "router",
        _route_from_router,
        {
            "code_tutor": "code_tutor",
            "planner": "planner",
            "analyst": "analyst",
        },
    )

    builder.add_conditional_edges(
        "code_tutor",
        tools_condition,
        {"tools": "code_tutor_tools", "__end__": END},
    )
    builder.add_conditional_edges(
        "planner",
        tools_condition,
        {"tools": "planner_tools", "__end__": END},
    )
    builder.add_conditional_edges(
        "analyst",
        tools_condition,
        {"tools": "analyst_tools", "__end__": END},
    )

    builder.add_edge("code_tutor_tools", "summarize")
    builder.add_edge("planner_tools", "summarize")
    builder.add_edge("analyst_tools", "summarize")

    builder.add_conditional_edges(
        "summarize",
        _route_after_summarize,
        {
            "code_tutor": "code_tutor",
            "planner": "planner",
            "analyst": "analyst",
        },
    )

    return builder.compile(checkpointer=MemorySaver())


multi_agent_graph = _build_multi_agent_graph()


def _chat_with_ollama_rag(
    request: ChatRequest, selected_agent: AgentName, intent: str, routing_reason: str
) -> ChatResponse:
    results = rag_service.query_knowledge_base(
        query=request.user_input,
        k=request.rag_k,
        user_id=request.user_id,
        is_admin=request.is_admin,
    )

    if request.strict_mode and not results:
        return ChatResponse(
            response=_strict_reject_message(),
            tool_calls=[],
            agent=selected_agent,
            intent=intent,
            routing_reason=routing_reason,
        )

    if results:
        context_chunks = "\n\n".join(
            f"[citation:{item['citation_id']}] {item['content']}" for item in results
        )
    else:
        context_chunks = "未检索到相关知识片段。"

    agent_prompt = AGENT_CONFIG[selected_agent]["prompt"]
    prompt = (
        f"角色要求：{agent_prompt}\n"
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

    llm = get_llm(selected_agent, enable_tools=False)
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
                return ChatResponse(
                    response=_strict_reject_message(),
                    tool_calls=[],
                    agent=selected_agent,
                    intent=intent,
                    routing_reason=routing_reason,
                )

    return ChatResponse(
        response=str(ai_msg.content or ""),
        tool_calls=[],
        agent=selected_agent,
        intent=intent,
        routing_reason=routing_reason,
    )


def chat_service(request: ChatRequest) -> ChatResponse:
    selected_agent, intent, routing_reason = route_intent(
        request.user_input, request.force_agent
    )
    if settings.CHAT_PROVIDER.lower() == "ollama":
        return _chat_with_ollama_rag(
            request,
            selected_agent=selected_agent,
            intent=intent,
            routing_reason=routing_reason,
        )

    state: State = {
        "messages": [{"role": "user", "content": request.user_input}],
        "selected_agent": selected_agent,
        "intent": intent,
        "routing_reason": routing_reason,
        "resolved_system_prompt": resolve_system_prompt(
            request.prompt_key, request.system_prompt
        ),
        "force_agent": request.force_agent,
    }
    thread_config = {"configurable": {"thread_id": request.thread_id}}

    token_user_id, token_is_admin, token_top_k = set_rag_request_context(
        request.user_id, request.is_admin, request.rag_k
    )
    try:
        result = multi_agent_graph.invoke(state, config=thread_config)
        final_agent = result.get("selected_agent", selected_agent)
        final_intent = result.get("intent", intent)
        final_reason = result.get("routing_reason", routing_reason)

        last_message = result["messages"][-1]
        return ChatResponse(
            response=message_text(last_message),
            tool_calls=collect_tool_calls(result.get("messages", [])),
            agent=final_agent,
            intent=final_intent,
            routing_reason=final_reason,
        )
    finally:
        reset_rag_request_context(token_user_id, token_is_admin, token_top_k)

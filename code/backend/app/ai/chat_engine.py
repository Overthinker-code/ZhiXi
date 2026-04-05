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
from app.ai.chat_tools import (
    TOOL_KEYS_BY_AGENT,
    get_tools_for_agent,
    get_llm,
    message_text,
    collect_tool_calls,
)
from app.services.rag_tools import set_rag_request_context, reset_rag_request_context
from app.services.rag_service import RAGService
from app.services.pending_actions import pending_action_store
from app.services.chat_semantic_cache import chat_semantic_cache

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
    llm = get_llm(
        agent,
        enable_tools=True,
        active_tools=state.get("active_tools"),
        temperature=state.get("temperature"),
        max_tokens=state.get("max_tokens"),
        top_p=state.get("top_p"),
        top_k=state.get("top_k"),
    )
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
    llm = get_llm(
        selected_agent,
        enable_tools=False,
        temperature=state.get("temperature"),
        max_tokens=state.get("max_tokens"),
        top_p=state.get("top_p"),
        top_k=state.get("top_k"),
    )
    summary_msg = llm.invoke([summary_prompt])
    return {"messages": [summary_msg]}


def _route_from_router(state: State):
    return state.get("selected_agent", "code_tutor")


def _route_after_summarize(state: State):
    return state.get("selected_agent", "code_tutor")


def _build_multi_agent_graph(active_tools: list[str] | None = None):
    code_tools = get_tools_for_agent("code_tutor", active_tools)
    planner_tools = get_tools_for_agent("planner", active_tools)
    analyst_tools = get_tools_for_agent("analyst", active_tools)

    builder = StateGraph(State)
    builder.add_node("router", router_node)
    builder.add_node("code_tutor", code_tutor_node)
    builder.add_node("planner", planner_node)
    builder.add_node("analyst", analyst_node)
    builder.add_node("code_tutor_tools", ToolNode(tools=code_tools))
    builder.add_node("planner_tools", ToolNode(tools=planner_tools))
    builder.add_node("analyst_tools", ToolNode(tools=analyst_tools))
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


def _build_selection_prompt(request: ChatRequest) -> str:
    selected = (request.selected_text or "").strip()
    context = (request.surrounding_context or "").strip()
    module = (request.course_module or "当前课程").strip()
    video_time = (request.video_time or "").strip()
    if not selected:
        return request.user_input

    prompt = (
        f"学生在学习《{module}》时选中了“{selected}”。\n"
        f"上下文片段：{context or '（无）'}\n"
    )
    if video_time:
        prompt += f"当前视频时间点：{video_time}\n"
    prompt += (
        "请用引导式、教学友好的口吻回答。"
        "如果适合，请补充一个简短示例帮助理解。"
    )
    return prompt


def _requires_hitl(intent: str, user_input: str) -> bool:
    if intent != "study_plan_adjustment":
        return False
    text = (user_input or "").lower()
    return any(k in text for k in ["进度", "复习", "计划", "落后", "冲刺"])


def _tool_status_text(agent: AgentName, active_tools: list[str] | None) -> tuple[list[str], list[str]]:
    allowed = TOOL_KEYS_BY_AGENT[agent]
    if not active_tools:
        return allowed, []
    enabled = [key for key in allowed if key in set(active_tools)]
    disabled = [key for key in allowed if key not in set(active_tools)]
    return enabled, disabled


def _chat_with_ollama_rag(
    request: ChatRequest, selected_agent: AgentName, intent: str, routing_reason: str
) -> ChatResponse:
    results = rag_service.query_knowledge_base(
        query=request.user_input,
        k=request.rag_k,
        user_id=request.user_id,
        is_admin=request.is_admin,
    )

    # 无检索结果时仍允许模型用自身知识作答；严格「仅引用库」仅在确有片段时生效
    strict_effective = bool(request.strict_mode) and bool(results)

    if results:
        context_chunks = "\n\n".join(
            f"[citation:{item['citation_id']}] {item['content']}" for item in results
        )
        kb_preamble = (
            "下列为与问题相关的知识库片段（有帮助时请引用并标注 [citation:x]）。\n"
            "若片段不足以完整回答，可结合你的通用知识补充，并区分资料内容与常识推断。"
        )
    else:
        context_chunks = "（本次未检索到相关知识库片段。）"
        kb_preamble = (
            "请基于你的通用知识与教学能力直接回答；不要编造不存在的课程文件内容。\n"
            "若用户问题强依赖某份未上传的专属材料，可简要说明并尽量给出通用层面的帮助。"
        )

    agent_prompt = AGENT_CONFIG[selected_agent]["prompt"]
    prompt = (
        f"角色要求：{agent_prompt}\n"
        f"{kb_preamble}\n"
        "要求：\n"
        "1. 回答应准确、有帮助；有片段时优先使用片段内容。\n"
        "2. 使用片段时请在关键结论后标注 [citation:x]。\n"
        "3. 无片段或信息不足时诚实说明，并尽量给出可用的解释或思路。\n\n"
        f"参考内容：\n{context_chunks}\n\n"
        f"用户问题：{request.user_input}"
    )
    if strict_effective:
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

    llm = get_llm(
        selected_agent,
        enable_tools=False,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        top_p=request.top_p,
        top_k=request.top_k,
    )
    ai_msg = llm.invoke(messages)
    if strict_effective:
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
    if request.selected_text:
        request.user_input = _build_selection_prompt(request)

    selected_agent, intent, routing_reason = route_intent(
        request.user_input, request.force_agent
    )

    cache_hit = chat_semantic_cache.get(request.user_input)
    if cache_hit:
        return ChatResponse(
            response=cache_hit.answer,
            tool_calls=[],
            agent=selected_agent,
            intent=intent,
            routing_reason=f"语义缓存命中（hit_count={cache_hit.hit_count}）",
            thoughts=["⚡ 语义缓存命中，直接返回历史高相似答案。"],
        )

    if settings.CHAT_PROVIDER.lower() == "ollama":
        response = _chat_with_ollama_rag(
            request,
            selected_agent=selected_agent,
            intent=intent,
            routing_reason=routing_reason,
        )
        chat_semantic_cache.put(request.user_input, response.response)
        return response

    state: State = {
        "messages": [{"role": "user", "content": request.user_input}],
        "selected_agent": selected_agent,
        "intent": intent,
        "routing_reason": routing_reason,
        "resolved_system_prompt": resolve_system_prompt(
            request.prompt_key, request.system_prompt
        ),
        "force_agent": request.force_agent,
        "active_tools": request.active_tools,
        "max_tokens": request.max_tokens,
        "temperature": request.temperature,
        "top_p": request.top_p,
        "top_k": request.top_k,
    }
    thread_config = {"configurable": {"thread_id": request.thread_id}}

    token_user_id, token_is_admin, token_top_k = set_rag_request_context(
        request.user_id, request.is_admin, request.rag_k
    )
    try:
        graph = (
            multi_agent_graph
            if not request.active_tools
            else _build_multi_agent_graph(request.active_tools)
        )
        result = graph.invoke(state, config=thread_config)
        final_agent = result.get("selected_agent", selected_agent)
        final_intent = result.get("intent", intent)
        final_reason = result.get("routing_reason", routing_reason)

        last_message = result["messages"][-1]
        response = ChatResponse(
            response=message_text(last_message),
            tool_calls=collect_tool_calls(result.get("messages", [])),
            agent=final_agent,
            intent=final_intent,
            routing_reason=final_reason,
            thoughts=[
                f"🤔 Router 判定意图：{final_intent}",
                f"📤 分配 Agent：{final_agent}",
            ],
        )
        if _requires_hitl(final_intent, request.user_input):
            action = pending_action_store.create(
                user_id=request.user_id or "anonymous",
                thread_id=request.thread_id,
                plan_text=response.response,
            )
            response.requires_confirmation = True
            response.pending_action_id = action.action_id
            response.thoughts.append("⏸ 已触发 HITL，请用户确认后写入日历。")

        chat_semantic_cache.put(request.user_input, response.response)
        return response
    finally:
        reset_rag_request_context(token_user_id, token_is_admin, token_top_k)


def stream_chat_events(request: ChatRequest):
    user_input = request.user_input
    if request.selected_text:
        user_input = _build_selection_prompt(request)
    selected_agent, intent, routing_reason = route_intent(user_input, request.force_agent)
    enabled_tools, disabled_tools = _tool_status_text(selected_agent, request.active_tools)

    yield {
        "type": "thought",
        "content": f"🤔 正在分析意图：识别为 {intent}，分配给 {selected_agent}",
    }
    if request.active_tools is not None:
        yield {
            "type": "thought",
            "content": f"🧰 工具开关状态：启用 {enabled_tools or ['none']}，禁用 {disabled_tools or ['none']}",
        }
        if not enabled_tools:
            yield {
                "type": "thought",
                "content": "⚠️ 当前可用工具为空，系统将降级为纯模型回答。",
            }

    try:
        response = chat_service(
            ChatRequest(
                **{
                    **request.model_dump(),
                    "user_input": user_input,
                    "force_agent": selected_agent,
                }
            )
        )
    except Exception as exc:
        yield {"type": "error", "content": f"处理失败：{exc}"}
        return

    for thought in response.thoughts:
        yield {"type": "thought", "content": thought}

    text = response.response or ""
    chunk_size = 24
    for i in range(0, len(text), chunk_size):
        yield {"type": "token", "content": text[i : i + chunk_size]}

    yield {
        "type": "final",
        "content": text,
        "agent": response.agent,
        "intent": response.intent,
        "routing_reason": response.routing_reason,
        "tool_calls": response.tool_calls,
        "requires_confirmation": response.requires_confirmation,
        "pending_action_id": response.pending_action_id,
    }

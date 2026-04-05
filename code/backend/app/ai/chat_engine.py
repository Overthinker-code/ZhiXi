from __future__ import annotations

import re
from typing import Any, cast

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode

from app.ai.chat_models import ChatRequest, ChatResponse, State, SupervisorDecision
from app.ai.chat_runtime import AGENT_CONFIG, resolve_system_prompt
from app.ai.chat_tools import (
    TOOL_KEYS_BY_AGENT,
    get_tools_for_agent,
    get_llm,
    message_text,
    collect_tool_calls,
)
from app.services.chat_model_factory import ChatModelFactory
from app.services.rag_service import RAGService
from app.services.rag_tools import set_rag_request_context, reset_rag_request_context
from app.services.pending_actions import pending_action_store
from app.services.chat_semantic_cache import chat_semantic_cache

rag_service = RAGService()

_WORKERS = frozenset({"code_tutor", "knowledge_mentor", "planner", "analyst"})
_MAX_SUPERVISOR_ENTRIES = 12

# 工具节点进入时推送（stream_mode=updates 下每个 ToolNode 执行前可见）
_TOOL_NODE_PIPELINE_MSG: dict[str, str] = {
    "code_tutor_tools": "【知识检索】代码导师正在调用知识库 / 联网 / 代码沙盒等工具。",
    "knowledge_mentor_tools": "【知识检索】学科讲师正在调用知识库或联网检索。",
    "planner_tools": "【知识检索】规划师正在检索知识库以支撑计划建议。",
    "analyst_tools": "【学情分析】分析师正在调用知识库或行为分析类工具。",
}

_JSON_OBJ = re.compile(r"\{[\s\S]*\}")


SUPERVISOR_SYSTEM_PROMPT = """你是「知曦学习系统」的主管 Supervisor（包工头），负责编排多位专员协同完成学生问题。

下属专员（每次只派其中一人发言，或判定可以结束）：
- code_tutor：编程语言报错、调试、运行失败、SQL/Python/Java/TS 等工程问题。
- knowledge_mentor：跨学科知识点讲解、概念辨析、教材型问答（经管、数理、文史、自然科学等），非代码排错优先找 TA。
- planner：学习计划、进度、复习节奏、里程碑与任务拆解。
- analyst：学习行为、状态评估、风险与数据化解读。

规则：
1. 结合完整对话历史判断「下一步谁最合适」；复合型需求可拆成多轮，一轮只派一名专员。
2. 若专员已在消息中充分覆盖且无需他人补位，输出 FINISH 进入汇总阶段。
3. 信息严重不足时可先派 knowledge_mentor 或 code_tutor 做澄清式回答，再视情况 FINISH 或继续派其他人。
4. 输出必须严格符合约定的结构化字段（next_agent / routing_reason / task_breakdown），不要输出其它闲聊。"""


def _rag_system_message(request: ChatRequest) -> SystemMessage:
    results = rag_service.query_knowledge_base(
        query=request.user_input,
        k=request.rag_k,
        user_id=request.user_id,
        is_admin=request.is_admin,
    )
    strict_effective = bool(request.strict_mode) and bool(results)
    if results:
        context_chunks = "\n\n".join(
            f"[citation:{item['citation_id']}] {item['content']}" for item in results
        )
        preamble = (
            "【知识库上下文】下列为与问题相关的知识库片段（有帮助时请引用并标注 [citation:x]）。\n"
            "若片段不足以完整回答，可结合通用知识补充，并区分资料与推断。\n"
        )
    else:
        context_chunks = "（本次未检索到相关知识库片段。）"
        preamble = (
            "【知识库上下文】未命中片段时，请基于通用知识与教学规范作答；勿编造未上传的专属材料。\n"
        )
    body = f"{preamble}\n{context_chunks}"
    if strict_effective:
        body += (
            "\n\n【严格模式】仅依据上述片段作答；关键结论须带 [citation:x]；"
            "证据不足则说明知识库证据不足。"
        )
    return SystemMessage(content=body)


def _parse_supervisor_decision(text: str) -> SupervisorDecision:
    raw = (text or "").strip()
    try:
        return SupervisorDecision.model_validate_json(raw)
    except Exception:
        m = _JSON_OBJ.search(raw)
        if m:
            return SupervisorDecision.model_validate_json(m.group())
        raise


def _invoke_supervisor_llm(state: State) -> SupervisorDecision:
    trim = state["messages"][-24:] if len(state["messages"]) > 24 else state["messages"]
    human_sys = SystemMessage(
        content=SUPERVISOR_SYSTEM_PROMPT
        + "\n\n当前 task_breakdown 草稿（可覆盖）：\n"
        + (state.get("task_breakdown") or "（空）")
    )
    messages = [human_sys, *trim]

    llm = ChatModelFactory.create(
        temperature=state.get("temperature") if state.get("temperature") is not None else 0.25,
        max_tokens=min(state.get("max_tokens") or 768, 1024),
    )
    try:
        structured = llm.with_structured_output(SupervisorDecision)
        decision = structured.invoke(messages)
        if isinstance(decision, SupervisorDecision):
            return decision
        if isinstance(decision, dict):
            return SupervisorDecision.model_validate(decision)
    except Exception:
        pass
    resp = llm.invoke(messages)
    return _parse_supervisor_decision(str(resp.content or ""))


def supervisor_node(state: State) -> dict[str, Any]:
    entries = state.get("supervisor_entries", 0) + 1
    thought_super = "【主管拆解】主管正在分析对话历史并决定下一步由哪位专员处理。"

    if entries > _MAX_SUPERVISOR_ENTRIES:
        return {
            "next_agent": "FINISH",
            "routing_reason": "已达到协作深度上限，结束派发并进入汇总。",
            "intermediate_steps": [
                thought_super,
                "【主管拆解】协作轮次已达上限，转入【汇总生成】阶段。",
            ],
            "supervisor_entries": entries,
        }

    fa = state.get("force_agent")
    if (
        fa
        and fa in _WORKERS
        and not state.get("force_agent_consumed")
    ):
        label = AGENT_CONFIG[fa]["label"]
        return {
            "next_agent": fa,
            "routing_reason": "用户指定由该专员优先处理。",
            "intermediate_steps": [
                thought_super,
                f"【主管拆解】按用户指定移交 → {label}（{fa}）。",
            ],
            "supervisor_entries": entries,
            "force_agent_consumed": True,
        }

    decision = _invoke_supervisor_llm(state)
    na = decision.next_agent
    if na not in _WORKERS and na != "FINISH":
        na = "FINISH"
    label = (
        AGENT_CONFIG[na]["label"]
        if na in _WORKERS
        else "结束协作"
    )
    step = (
        f"【主管拆解】路由说明：{decision.routing_reason.strip() or '主管决策'}\n"
        f"→ 下一步：{'【汇总生成】' if na == 'FINISH' else f'{label}（{na}）'}"
    )
    if decision.task_breakdown.strip():
        step += f"\n子任务清单：{decision.task_breakdown.strip()}"

    return {
        "next_agent": na,
        "task_breakdown": decision.task_breakdown.strip() or state.get("task_breakdown", ""),
        "routing_reason": decision.routing_reason.strip(),
        "intent": "supervisor_route",
        "intermediate_steps": [thought_super, step],
        "supervisor_entries": entries,
    }


def finalize_node(state: State) -> dict[str, Any]:
    llm = ChatModelFactory.create(
        temperature=state.get("temperature"),
        max_tokens=state.get("max_tokens"),
    )
    sys = SystemMessage(
        content=(
            "你是知曦学习系统的主管，负责向学生输出最终答复。\n"
            "请综合对话中各位专员已给出的结论与建议，整理成结构清晰、语气友好、可直接展示的回复；"
            "避免暴露内部角色名与流程术语。\n"
            "若仍有未覆盖的问题，诚实说明并给出可行建议。"
        )
    )
    prelude: list = [sys]
    resolved = (state.get("resolved_system_prompt") or "").strip()
    if resolved:
        prelude.insert(0, SystemMessage(content=f"全局辅导偏好：\n{resolved}"))
    msg = llm.invoke([*prelude, *state["messages"]])
    return {
        "messages": [msg],
        "selected_agent": "supervisor",
        "intent": "final_summary",
        "routing_reason": state.get("routing_reason", "") or "协作汇总",
        "intermediate_steps": [
            "【汇总生成】主管正在综合各专员发言，生成面向学生的最终答复。"
        ],
    }


_WORKER_DONE_TAG: dict[str, str] = {
    "code_tutor": "【代码验证】代码导师本轮处理完成，结果已同步至主管。",
    "knowledge_mentor": "【学科讲解】学科知识讲师本轮处理完成，已同步至主管。",
    "planner": "【学习规划】学习规划师本轮处理完成，已同步至主管。",
    "analyst": "【学情分析】学习分析师本轮处理完成，已同步至主管。",
}


def _team_member_prefix(agent: str) -> str:
    label = AGENT_CONFIG[agent]["label"]
    return (
        f"你是团队成员「{label}」（{agent}）。主管已将你加入协作线程。\n"
        "请基于对话与知识库上下文完成本轮任务，将结论写入助手消息；"
        "保持专业、简洁，勿编造未给出的数据。"
    )


def _invoke_worker(state: State, agent: str) -> dict[str, Any]:
    role_prompt = AGENT_CONFIG[agent]["prompt"]
    merged = f"{_team_member_prefix(agent)}\n\n{role_prompt}"
    resolved = (state.get("resolved_system_prompt") or "").strip()
    if resolved:
        merged = f"{resolved}\n\n{merged}"
    sys = SystemMessage(content=merged)
    llm = get_llm(
        agent,
        enable_tools=True,
        active_tools=state.get("active_tools"),
        temperature=state.get("temperature"),
        max_tokens=state.get("max_tokens"),
        top_p=state.get("top_p"),
        top_k=state.get("top_k"),
    )
    ai_msg = llm.invoke([sys, *state["messages"]])
    return {
        "messages": [ai_msg],
        "selected_agent": agent,
        "intent": f"worker_{agent}",
        "collaboration_last_worker": agent,
        "intermediate_steps": [
            _WORKER_DONE_TAG.get(
                agent,
                f"【专员】{AGENT_CONFIG[agent]['label']} 本轮处理完成，已同步至主管。",
            )
        ],
    }


def _worker_tools_or_supervisor(state: State) -> str:
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and getattr(last, "tool_calls", None):
        return "tools"
    return "supervisor"


def _supervisor_branch(state: State) -> str:
    n = (state.get("next_agent") or "FINISH").strip()
    if n == "FINISH":
        return "finalize"
    if n in _WORKERS:
        return n
    return "finalize"


def _make_worker_node(agent_name: str):
    def _run(state: State) -> dict[str, Any]:
        return _invoke_worker(state, agent_name)

    return _run


def _build_supervisor_graph(active_tools: list[str] | None = None):
    builder = StateGraph(State)
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("finalize", finalize_node)

    worker_specs = [
        ("code_tutor", "code_tutor_tools"),
        ("knowledge_mentor", "knowledge_mentor_tools"),
        ("planner", "planner_tools"),
        ("analyst", "analyst_tools"),
    ]
    for name, tools_node in worker_specs:
        builder.add_node(name, _make_worker_node(name))
        tlist = get_tools_for_agent(name, active_tools)
        builder.add_node(tools_node, ToolNode(tools=tlist))
        builder.add_conditional_edges(
            name,
            _worker_tools_or_supervisor,
            {"tools": tools_node, "supervisor": "supervisor"},
        )
        builder.add_edge(tools_node, name)

    builder.add_edge(START, "supervisor")
    builder.add_conditional_edges(
        "supervisor",
        _supervisor_branch,
        {
            "code_tutor": "code_tutor",
            "knowledge_mentor": "knowledge_mentor",
            "planner": "planner",
            "analyst": "analyst",
            "finalize": "finalize",
        },
    )
    builder.add_edge("finalize", END)
    return builder.compile(checkpointer=MemorySaver())


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


def _requires_hitl(
    intent: str,
    user_input: str,
    task_breakdown: str = "",
    last_worker: str = "",
) -> bool:
    if (last_worker or "") != "planner":
        return False
    blob = f"{user_input or ''}\n{task_breakdown or ''}".lower()
    return any(k in blob for k in ["进度", "复习", "计划", "落后", "冲刺"])


def _tool_status_text(
    active_tools: list[str] | None,
) -> tuple[list[str], list[str]]:
    allowed = sorted({k for keys in TOOL_KEYS_BY_AGENT.values() for k in keys})
    if not active_tools:
        return allowed, []
    active = set(active_tools)
    enabled = [k for k in allowed if k in active]
    disabled = [k for k in allowed if k not in active]
    return enabled, disabled


def _initial_state(request: ChatRequest, user_text: str) -> State:
    rag_msg = _rag_system_message(request)
    preset = resolve_system_prompt(request.prompt_key, request.system_prompt)
    messages: list = [rag_msg, HumanMessage(content=user_text)]
    return cast(
        State,
        {
            "messages": messages,
            "next_agent": "",
            "task_breakdown": "",
            "intermediate_steps": [],
            "selected_agent": "code_tutor",
            "intent": "",
            "routing_reason": "",
            "resolved_system_prompt": preset or "",
            "force_agent": request.force_agent,
            "force_agent_consumed": False,
            "active_tools": request.active_tools,
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
            "top_p": request.top_p,
            "top_k": request.top_k,
            "supervisor_entries": 0,
            "strict_mode": bool(request.strict_mode),
            "collaboration_last_worker": "",
        },
    )


def chat_service(request: ChatRequest) -> ChatResponse:
    if request.selected_text:
        request.user_input = _build_selection_prompt(request)

    cache_hit = chat_semantic_cache.get(request.user_input)
    if cache_hit:
        return ChatResponse(
            response=cache_hit.answer,
            tool_calls=[],
            agent="supervisor",
            intent="semantic_cache",
            routing_reason=f"语义缓存命中（hit_count={cache_hit.hit_count}）",
            thoughts=["⚡ 语义缓存命中，直接返回历史高相似答案。"],
        )

    graph = _build_supervisor_graph(request.active_tools)
    thread_config = {"configurable": {"thread_id": request.thread_id}}
    initial = _initial_state(request, request.user_input)

    token_user_id, token_is_admin, token_top_k = set_rag_request_context(
        request.user_id, request.is_admin, request.rag_k
    )
    try:
        result = graph.invoke(initial, config=thread_config)
        final_text = message_text(result["messages"][-1])
        thoughts = list(result.get("intermediate_steps") or [])
        response = ChatResponse(
            response=final_text,
            tool_calls=collect_tool_calls(result.get("messages", [])),
            agent=result.get("selected_agent", "supervisor"),
            intent=result.get("intent", "collaborative_supervisor"),
            routing_reason=result.get("routing_reason", "") or "协作完成",
            thoughts=thoughts,
        )
        if _requires_hitl(
            response.intent,
            request.user_input,
            result.get("task_breakdown") or "",
            result.get("collaboration_last_worker") or "",
        ):
            action = pending_action_store.create(
                user_id=request.user_id or "anonymous",
                thread_id=request.thread_id,
                plan_text=response.response,
            )
            response.requires_confirmation = True
            response.pending_action_id = action.action_id
            response.thoughts = [
                *response.thoughts,
                "⏸ 已触发 HITL，请用户确认后写入日历。",
            ]

        chat_semantic_cache.put(request.user_input, response.response)
        return response
    finally:
        reset_rag_request_context(token_user_id, token_is_admin, token_top_k)


def stream_chat_events(request: ChatRequest):
    user_input = request.user_input
    if request.selected_text:
        user_input = _build_selection_prompt(request)
    req = request.model_copy(update={"user_input": user_input})

    enabled_tools, disabled_tools = _tool_status_text(req.active_tools)
    yield {
        "type": "thought",
        "content": "【流水线】多智能体协作已启动（Supervisor + 专员 + 汇总）。",
        "stage": "pipeline_start",
    }
    yield {
        "type": "thought",
        "content": "【知识检索】已根据当前问题检索知识库并将上下文注入协作线程（首条系统消息）。",
        "stage": "kb_inject",
    }
    if req.active_tools is not None:
        yield {
            "type": "thought",
            "content": f"【工具策略】启用工具：{enabled_tools or ['none']}；已关闭：{disabled_tools or ['none']}",
            "stage": "tool_policy",
        }
        if not enabled_tools:
            yield {
                "type": "thought",
                "content": "【工具策略】当前过滤后无可用工具，专员将仅依赖模型能力。",
                "stage": "tool_policy",
            }

    cache_hit = chat_semantic_cache.get(req.user_input)
    if cache_hit:
        yield {
            "type": "thought",
            "content": "【流水线】语义缓存命中，跳过协作图执行。",
            "stage": "cache",
        }
        text = cache_hit.answer
        for i in range(0, len(text), 24):
            yield {"type": "token", "content": text[i : i + 24]}
        yield {
            "type": "final",
            "content": text,
            "agent": "supervisor",
            "intent": "semantic_cache",
            "routing_reason": "语义缓存",
            "tool_calls": [],
            "requires_confirmation": False,
            "pending_action_id": None,
        }
        return

    graph = _build_supervisor_graph(req.active_tools)
    thread_config = {"configurable": {"thread_id": str(req.thread_id)}}
    initial = _initial_state(req, req.user_input)

    token_user_id, token_is_admin, token_top_k = set_rag_request_context(
        req.user_id, req.is_admin, req.rag_k
    )
    final_state: dict | None = None
    emitted_tool_nodes: set[str] = set()
    try:
        # updates：每跑完一个节点即推送，前端可「流水线」逐条显示
        for chunk in graph.stream(
            initial, config=thread_config, stream_mode="updates"
        ):
            if not isinstance(chunk, dict):
                continue
            for node_name, data in chunk.items():
                if not isinstance(node_name, str):
                    continue
                if node_name.endswith("_tools") and node_name not in emitted_tool_nodes:
                    emitted_tool_nodes.add(node_name)
                    yield {
                        "type": "thought",
                        "content": _TOOL_NODE_PIPELINE_MSG.get(
                            node_name,
                            "【工具执行】正在运行后端工具节点。",
                        ),
                        "stage": "tool_run",
                    }
                if isinstance(data, dict):
                    for s in data.get("intermediate_steps") or []:
                        yield {"type": "thought", "content": s}
        try:
            snap = graph.get_state(thread_config)
            if snap is not None and getattr(snap, "values", None) is not None:
                final_state = dict(snap.values)
        except Exception:
            final_state = None
    except Exception as exc:
        yield {"type": "error", "content": f"处理失败：{exc}"}
        return
    finally:
        reset_rag_request_context(token_user_id, token_is_admin, token_top_k)

    if not final_state:
        yield {"type": "error", "content": "协作图未返回状态"}
        return

    text = message_text(final_state["messages"][-1])
    chat_semantic_cache.put(req.user_input, text)

    chunk_size = 24
    for i in range(0, len(text), chunk_size):
        yield {"type": "token", "content": text[i : i + chunk_size]}

    resp = ChatResponse(
        response=text,
        tool_calls=collect_tool_calls(final_state.get("messages", [])),
        agent=final_state.get("selected_agent", "supervisor"),
        intent=final_state.get("intent", "collaborative_supervisor"),
        routing_reason=final_state.get("routing_reason", "") or "协作完成",
        thoughts=list(final_state.get("intermediate_steps") or []),
    )
    if _requires_hitl(
        resp.intent,
        req.user_input,
        final_state.get("task_breakdown") or "",
        final_state.get("collaboration_last_worker") or "",
    ):
        action = pending_action_store.create(
            user_id=req.user_id or "anonymous",
            thread_id=req.thread_id,
            plan_text=resp.response,
        )
        resp.requires_confirmation = True
        resp.pending_action_id = action.action_id

    yield {
        "type": "final",
        "content": text,
        "agent": resp.agent,
        "intent": resp.intent,
        "routing_reason": resp.routing_reason,
        "tool_calls": resp.tool_calls,
        "requires_confirmation": resp.requires_confirmation,
        "pending_action_id": resp.pending_action_id,
    }

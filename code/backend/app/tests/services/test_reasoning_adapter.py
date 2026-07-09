from app.services.reasoning_adapter import (
    ReasoningAdapterContext,
    ReasoningProcessNormalizer,
    contains_supplier_context,
    guard_answer_delta,
    guarded_fallback_answer,
    normalize_reasoning_to_product_process,
    sanitize_visible_answer_delta,
)


def test_supplier_reasoning_is_sanitized_to_product_process() -> None:
    context = ReasoningAdapterContext(
        message="你能做什么？",
        mode="tutor",
        tools={"courseRag": False},
        course_context={"useCourseRag": False},
    )
    raw = "我是小米助手，可以连接米家App、HyperOS、小米手机、手环、电视和智能家居设备。"

    delta = normalize_reasoning_to_product_process(raw, context)

    assert delta is not None
    assert delta.sanitized is True
    assert delta.phase_id == "plan_answer"
    assert "小米" not in delta.summary
    assert "米家" not in delta.summary
    assert "HyperOS" not in delta.summary
    assert "智能家居" not in delta.summary
    assert "智屿" in delta.summary or "学习助手" in delta.summary


def test_process_normalizer_deduplicates_same_stage_summary() -> None:
    context = ReasoningAdapterContext(message="解释数据库索引", mode="tutor")
    normalizer = ReasoningProcessNormalizer(context)

    first = normalizer.ingest("需要组织回答结构，先解释结论再给例子。")
    second = normalizer.ingest("需要组织回答结构，先解释结论再给例子。")

    assert first is not None
    assert first.phase_id == "plan_answer"
    assert second is None


def test_supplier_answer_guard_blocks_unrelated_provider_identity() -> None:
    context = ReasoningAdapterContext(message="你能做什么？", mode="tutor")
    text = "我是小米助手，可以帮你管理米家智能家居。"

    guarded, blocked = guard_answer_delta(text, context)

    assert blocked is True
    assert guarded == ""
    fallback = guarded_fallback_answer(context)
    assert contains_supplier_context(fallback) is False
    assert "课程问答" in fallback
    assert "作业批改" in fallback
    assert "资料生成" in fallback


def test_visible_answer_sanitizer_removes_think_and_internal_logs() -> None:
    context = ReasoningAdapterContext(message="解析世界模型的近期研究", mode="deep_research")
    text = (
        "<think>用户希望我先走 intent_classifier，然后注入 course_context。</think>\n"
        "【知识检索】已根据当前问题检索知识库并将上下文注入协作线程。\n"
        "我来梳理一下对这个问题的分析思路。\n\n"
        "第一步：明确“世界模型”的含义边界。"
    )

    sanitized, blocked = sanitize_visible_answer_delta(text, context)

    assert blocked is True
    assert "<think>" not in sanitized
    assert "intent_classifier" not in sanitized
    assert "course_context" not in sanitized
    assert "知识检索" not in sanitized
    assert "第一步" in sanitized

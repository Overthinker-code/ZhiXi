from __future__ import annotations

from app.ai.chat_models import ChatResponse


def build_demo_chat_response(user_input: str) -> ChatResponse:
    topic = (user_input or "当前知识点").strip()[:24] or "当前知识点"
    answer = (
        f"### 演示模式答复\n"
        f"- 当前问题聚焦在：`{topic}`\n"
        "- 我已切换到演示兜底链路，因此优先返回稳定可展示的讲解结果。\n"
        "- 如果这是课堂答辩场景，可以继续点击下方推荐动作，让系统进一步生成练习题、例子或复习建议。\n\n"
        "#### 建议理解路径\n"
        "1. 先明确这个知识点的定义与适用场景。\n"
        "2. 再通过一个最小例子理解它如何落到题目或课堂实践里。\n"
        "3. 最后用 2-3 道递进练习验证是否真的掌握。"
    )
    return ChatResponse(
        response=answer,
        agent="supervisor",
        intent="demo_mode",
        routing_reason="演示模式已启用，返回稳定兜底答案。",
        thoughts=["【演示模式】已启用稳定兜底回复，跳过实时模型执行。"],
        citations=[],
        confidence="medium",
        grounding_mode="general",
        suggestions=[
            f"围绕 {topic} 给我一个更贴近课堂的例子。",
            f"基于 {topic} 给我 3 道递进练习题。",
            f"把 {topic} 总结成考前速记卡片。",
        ],
    )

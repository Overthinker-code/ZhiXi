from typing import Any, List
import base64

from langchain.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

from app.core.config import settings
from app.ai.chat_runtime import AgentName
from app.services.chat_model_factory import ChatModelFactory
from app.services.rag_tools import query_knowledge_base
from app.services.behavior_analysis import behavior_service

search = DuckDuckGoSearchRun()
_base_llm = ChatModelFactory.create()


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


TOOLS_BY_AGENT: dict[AgentName, list] = {
    "code_tutor": [query_knowledge_base, search_web],
    "planner": [query_knowledge_base],
    "analyst": [query_knowledge_base, analyze_student_behavior],
}


def get_llm(agent: AgentName, enable_tools: bool):
    if not enable_tools:
        return _base_llm
    if settings.CHAT_PROVIDER.lower() == "ollama":
        return _base_llm
    return _base_llm.bind_tools(TOOLS_BY_AGENT[agent])


def message_text(message: Any) -> str:
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(item) for item in content)
    return str(content)


def collect_tool_calls(messages: list) -> List[dict]:
    collected: List[dict] = []
    for message in messages:
        tool_calls = getattr(message, "tool_calls", None) or []
        for call in tool_calls:
            if isinstance(call, dict):
                collected.append(call)
            else:
                collected.append({"raw": str(call)})
    return collected

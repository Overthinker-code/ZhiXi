from typing import Any, List
import base64
import subprocess
import tempfile
import textwrap

from langchain.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

from app.core.config import settings
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
def execute_code_sandbox(code: str, language: str = "python") -> str:
    """Execute code in a sandbox-like subprocess with strict limits."""
    if language.lower() not in {"python", "py"}:
        return "当前演示版沙盒仅支持 Python 代码执行。"
    safe_code = textwrap.dedent(code or "").strip()
    if not safe_code:
        return "未检测到可执行代码。"
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=True) as f:
            f.write(safe_code)
            f.flush()
            result = subprocess.run(
                ["python", "-I", f.name],
                capture_output=True,
                text=True,
                timeout=5,
            )
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        if result.returncode != 0:
            return f"沙盒执行失败（code={result.returncode}）：{stderr[:800]}"
        return f"沙盒执行成功：\n{stdout[:1200] or '(无输出)'}"
    except subprocess.TimeoutExpired:
        return "沙盒执行超时（>5秒），已终止。"
    except Exception as exc:
        return f"沙盒执行异常：{exc}"


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


TOOL_REGISTRY: dict[str, Any] = {
    "knowledge_base": query_knowledge_base,
    "web_search": search_web,
    "behavior_analysis": analyze_student_behavior,
    "code_sandbox": execute_code_sandbox,
}

TOOL_KEYS_BY_AGENT: dict[str, list[str]] = {
    "code_tutor": ["knowledge_base", "web_search", "code_sandbox"],
    "knowledge_mentor": ["knowledge_base", "web_search"],
    "planner": ["knowledge_base"],
    "analyst": ["knowledge_base", "behavior_analysis"],
}

TOOLS_BY_AGENT: dict[str, list] = {
    agent: [TOOL_REGISTRY[key] for key in keys]
    for agent, keys in TOOL_KEYS_BY_AGENT.items()
}


def get_tools_for_agent(agent: str, active_tools: list[str] | None = None) -> list:
    tool_keys = TOOL_KEYS_BY_AGENT.get(agent) or ["knowledge_base"]
    if not active_tools:
        return [TOOL_REGISTRY[key] for key in tool_keys]
    active = set(active_tools)
    filtered = [TOOL_REGISTRY[key] for key in tool_keys if key in active]
    # Ensure the agent always has at least one safe baseline tool.
    return filtered or [query_knowledge_base]


def get_llm(
    agent: str,
    enable_tools: bool,
    *,
    active_tools: list[str] | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    top_p: float | None = None,
    top_k: int | None = None,
):
    llm = (
        _base_llm
        if all(v is None for v in (temperature, max_tokens, top_p, top_k))
        else ChatModelFactory.create(
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            top_k=top_k,
        )
    )
    if not enable_tools:
        return llm
    if settings.CHAT_PROVIDER.lower() == "ollama":
        return llm
    return llm.bind_tools(get_tools_for_agent(agent, active_tools))


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

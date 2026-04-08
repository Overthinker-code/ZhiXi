from typing import Any, List, Optional
import base64
import subprocess
import tempfile
import textwrap

from langchain.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

from app.core.config import settings
from app.services.chat_model_factory import ChatModelFactory
from app.services.rag_tools import run_query_knowledge_base
from app.services.behavior_analysis import behavior_service
from app.services.rag_service import RAGService

search = DuckDuckGoSearchRun()
_base_llm = ChatModelFactory.create()
rag_service = RAGService()


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


def make_query_knowledge_base_tool(
    user_id: Optional[str],
    is_admin: bool,
    rag_top_k: int,
):
    """按请求闭包 RAG 上下文，避免 ContextVar 在 LangGraph/异步边界 reset 崩溃。"""

    @tool
    def query_knowledge_base(question: str) -> str:
        """RAG retrieval tool. Returns retrieved chunks with citation labels."""
        return run_query_knowledge_base(
            question,
            user_id=user_id,
            is_admin=is_admin,
            top_k=rag_top_k,
        )

    return query_knowledge_base


def make_search_uploaded_document_tool(
    *,
    user_id: Optional[str],
    is_admin: bool,
    thread_id: str,
    current_file_id: Optional[str],
):
    @tool
    def search_uploaded_document(
        query: str,
        file_id: str = "",
        top_k: int = 3,
    ) -> str:
        """
        当用户提问关于其上传文档时，检索 thread 级临时知识库。
        参数：query（问题）、file_id（可选，默认当前挂载文件）、top_k（返回片段数）。
        """
        effective_file_id = (file_id or current_file_id or "").strip()
        if not effective_file_id:
            return "未提供 file_id，无法检索上传文档。"
        hits = rag_service.search_uploaded_document(
            query=query,
            file_id=effective_file_id,
            thread_id=thread_id,
            user_id=user_id,
            is_admin=is_admin,
            top_k=max(1, min(int(top_k or 3), 8)),
        )
        if not hits:
            return "未在该文档中检索到相关内容。"
        lines = []
        for item in hits:
            lines.append(
                f"[doc:{item.get('citation_id')}] "
                f"{item.get('content', '')}\n"
                f"(source={item.get('source')}, chunk={item.get('chunk_id')})"
            )
        return "\n\n".join(lines)

    return search_uploaded_document


TOOL_REGISTRY: dict[str, Any] = {
    "web_search": search_web,
    "behavior_analysis": analyze_student_behavior,
    "code_sandbox": execute_code_sandbox,
}

TOOL_KEYS_BY_AGENT: dict[str, list[str]] = {
    "code_tutor": ["knowledge_base", "web_search", "code_sandbox"],
    "knowledge_mentor": ["knowledge_base", "web_search"],
    "planner": ["knowledge_base"],
    "analyst": ["knowledge_base", "behavior_analysis"],
    "doc_researcher": ["search_uploaded_document"],
    "quiz_master": ["knowledge_base"],
}


def _resolve_tool_impl(
    key: str,
    *,
    rag_user_id: Optional[str],
    rag_is_admin: bool,
    rag_k: int,
    thread_id: str,
    current_file_id: Optional[str],
) -> Any:
    if key == "knowledge_base":
        return make_query_knowledge_base_tool(rag_user_id, rag_is_admin, rag_k)
    if key == "search_uploaded_document":
        return make_search_uploaded_document_tool(
            user_id=rag_user_id,
            is_admin=rag_is_admin,
            thread_id=thread_id,
            current_file_id=current_file_id,
        )
    return TOOL_REGISTRY[key]


def get_tools_for_agent(
    agent: str,
    active_tools: list[str] | None = None,
    *,
    rag_user_id: Optional[str] = None,
    rag_is_admin: bool = False,
    rag_k: int = 4,
    thread_id: str = "default",
    current_file_id: Optional[str] = None,
) -> list:
    tool_keys = TOOL_KEYS_BY_AGENT.get(agent) or ["knowledge_base"]
    if not active_tools:
        return [
            _resolve_tool_impl(
                key,
                rag_user_id=rag_user_id,
                rag_is_admin=rag_is_admin,
                rag_k=rag_k,
                thread_id=thread_id,
                current_file_id=current_file_id,
            )
            for key in tool_keys
        ]
    active = set(active_tools)
    filtered_keys = [key for key in tool_keys if key in active]
    keys = filtered_keys or ["knowledge_base"]
    return [
        _resolve_tool_impl(
            key,
            rag_user_id=rag_user_id,
            rag_is_admin=rag_is_admin,
            rag_k=rag_k,
            thread_id=thread_id,
            current_file_id=current_file_id,
        )
        for key in keys
    ]


def get_llm(
    agent: str,
    enable_tools: bool,
    *,
    active_tools: list[str] | None = None,
    rag_user_id: Optional[str] = None,
    rag_is_admin: bool = False,
    rag_k: int = 4,
    thread_id: str = "default",
    current_file_id: Optional[str] = None,
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
    return llm.bind_tools(
        get_tools_for_agent(
            agent,
            active_tools,
            rag_user_id=rag_user_id,
            rag_is_admin=rag_is_admin,
            rag_k=rag_k,
            thread_id=thread_id,
            current_file_id=current_file_id,
        )
    )


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

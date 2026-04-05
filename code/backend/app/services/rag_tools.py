from langchain.tools import tool
from contextvars import ContextVar
from typing import Optional

from app.services.rag_service import RAGService

rag_service = RAGService()
_rag_user_id_ctx: ContextVar[Optional[str]] = ContextVar("rag_user_id", default=None)
_rag_is_admin_ctx: ContextVar[bool] = ContextVar("rag_is_admin", default=False)
_rag_top_k_ctx: ContextVar[int] = ContextVar("rag_top_k", default=3)


def set_rag_request_context(user_id: Optional[str], is_admin: bool, top_k: int = 3):
    token_user_id = _rag_user_id_ctx.set(user_id)
    token_is_admin = _rag_is_admin_ctx.set(is_admin)
    token_top_k = _rag_top_k_ctx.set(max(1, int(top_k)))
    return token_user_id, token_is_admin, token_top_k


def reset_rag_request_context(token_user_id, token_is_admin, token_top_k) -> None:
    _rag_user_id_ctx.reset(token_user_id)
    _rag_is_admin_ctx.reset(token_is_admin)
    _rag_top_k_ctx.reset(token_top_k)


@tool
def query_knowledge_base(question: str) -> str:
    """RAG retrieval tool. Returns retrieved chunks with citation labels."""
    results = rag_service.query_knowledge_base(
        query=question,
        k=_rag_top_k_ctx.get(),
        user_id=_rag_user_id_ctx.get(),
        is_admin=_rag_is_admin_ctx.get(),
    )

    if not results:
        return (
            "当前知识库未检索到与该问题直接相关的条目。"
            "请基于你的通用知识与上下文继续协助用户；"
            "若需要课程专属事实，可提示用户上传相关参考文件。"
        )

    chunk_lines = []
    refs = []
    for item in results:
        citation_id = item["citation_id"]
        chunk_text = item["content"].strip()
        source = item.get("source") or "unknown"
        chunk_id = item.get("chunk_id")

        chunk_lines.append(f"[citation:{citation_id}] {chunk_text}")
        refs.append(f"[citation:{citation_id}] source={source}, chunk_id={chunk_id}")

    chunk_block = "\n\n".join(chunk_lines)
    refs_block = "\n".join(refs)
    return (
        f"问题：{question}\n\n"
        f"可参考知识片段：\n{chunk_block}\n\n"
        f"引用索引：\n{refs_block}\n\n"
        "请在最终回答中保留 citation 标记。"
    )

from typing import Optional

from app.services.rag_service import RAGService

rag_service = RAGService()


def run_query_knowledge_base(
    question: str,
    *,
    user_id: Optional[str],
    is_admin: bool,
    top_k: int,
) -> str:
    """
    知识库检索（纯函数，不依赖 ContextVar）。
    供 LangGraph 内通过闭包工具调用，避免异步/多任务下 Token 跨上下文 reset 崩溃。
    """
    try:
        k = max(1, int(top_k))
        results = rag_service.query_knowledge_base(
            query=question,
            k=k,
            user_id=user_id,
            is_admin=is_admin,
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
        body = (
            f"问题：{question}\n\n"
            f"可参考知识片段：\n{chunk_block}\n\n"
            f"引用索引：\n{refs_block}\n\n"
            "请在最终回答中保留 citation 标记。"
        )
        if len(body) > 12000:
            return body[:12000] + "\n\n…[检索结果过长已截断]"
        return body
    except Exception as e:
        return f"工具执行失败（知识库检索）：{e!s}"

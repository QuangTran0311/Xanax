"""
RAG "phòng tư liệu" — kho tài liệu dự án dùng để truy hồi đúng thông tin cần
thiết trước khi agent xử lý, thay vì nhét toàn bộ tài liệu vào prompt (tốn token).

Dùng lại bộ tokenizer keyword-overlap của core/matcher.py — không thêm
dependency embedding/vector store mới.
"""
from __future__ import annotations

from core.matcher import _tokenize
from hub.database import list_knowledge_documents


def _chunk_score(query_tokens: set[str], text: str) -> float:
    if not query_tokens or not text:
        return 0.0
    text_tokens = _tokenize(text)
    if not text_tokens:
        return 0.0
    matched = query_tokens & text_tokens
    return len(matched) / len(query_tokens)


async def rag_search(
    query: str,
    project_id: int | None = None,
    top_k: int = 3,
    min_score: float = 0.08,
) -> list[dict]:
    """Trả về top_k tài liệu (knowledge_documents) liên quan nhất tới `query`.

    Tài liệu gắn project_id=None coi là dùng chung cho mọi dự án.
    """
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    docs = await list_knowledge_documents(project_id=project_id)
    scored: list[dict] = []
    for d in docs:
        text = f"{d.get('title', '')} {d.get('content', '')} {d.get('tags', '')}"
        score = _chunk_score(query_tokens, text)
        if score >= min_score:
            scored.append({**d, "score": round(score, 3)})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def format_rag_context(results: list[dict]) -> str:
    if not results:
        return ""
    parts = ["\n---\n## Tư liệu liên quan (từ phòng lưu trữ RAG)"]
    for r in results:
        parts.append(f"\n### {r['title']} (độ liên quan {r['score']})\n{r['content']}")
    return "\n".join(parts)

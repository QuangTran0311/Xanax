"""
MCP Server — Hermes Hub
Expose các tool để Hermes CLI tương tác với Hub qua Model Context Protocol.
"""
import asyncio
import json

from mcp.server.fastmcp import FastMCP

from app.config import settings
from app.db.session import AsyncSessionLocal
from app.services import episode as episode_svc
from app.services import model as model_svc
from app.services import session as session_svc
from app.meeting import room as room_mod
from app.db.models.soul import SoulKnowledge
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

mcp = FastMCP("hermes-hub")


# ── SESSION ────────────────────────────────────────────────────────────────────

@mcp.tool()
async def create_session(user_id: str = "hermes-cli", title: str | None = None) -> str:
    """Tạo session mới trong Hub để lưu lịch sử cuộc hội thoại."""
    async with AsyncSessionLocal() as db:
        session = await session_svc.create_session(db, user_id, title)
        return json.dumps({"id": session.id, "title": session.title, "status": session.status})


@mcp.tool()
async def end_session(session_id: str, reflection: str | None = None) -> str:
    """Kết thúc session và distill thành episodic memory."""
    async with AsyncSessionLocal() as db:
        await session_svc.end_session(db, session_id)
        episode = await episode_svc.distill_to_episode(db, session_id, reflection)
        return json.dumps({"ended": True, "episode_id": episode.id})


# ── SOUL ───────────────────────────────────────────────────────────────────────

@mcp.tool()
async def get_soul(key: str | None = None) -> str:
    """Lấy SOUL knowledge của Hermes từ database (bộ nhớ dài hạn)."""
    async with AsyncSessionLocal() as db:
        stmt = select(SoulKnowledge).where(
            SoulKnowledge.agent_id == "hermes",
            SoulKnowledge.is_active.is_(True),
        )
        if key:
            stmt = stmt.where(SoulKnowledge.key == key)
        result = await db.execute(stmt)
        entries = [{"key": e.key, "content": e.content} for e in result.scalars()]
        return json.dumps(entries)


@mcp.tool()
async def update_soul(key: str, content: str, category: str = "learned") -> str:
    """Cập nhật hoặc thêm SOUL knowledge mới cho Hermes."""
    async with AsyncSessionLocal() as db:
        stmt = (
            insert(SoulKnowledge)
            .values(agent_id="hermes", key=key, category=category, content=content)
            .on_conflict_do_update(
                constraint="soul_knowledge_agentId_key_key",
                set_={"content": content, "version": SoulKnowledge.version + 1},
            )
            .returning(SoulKnowledge.key, SoulKnowledge.version)
        )
        result = await db.execute(stmt)
        await db.commit()
        row = result.one()
        return json.dumps({"key": row.key, "version": row.version})


# ── EPISODIC MEMORY ────────────────────────────────────────────────────────────

@mcp.tool()
async def get_episodes(limit: int = 10) -> str:
    """Lấy lịch sử episodic memory — những gì Hermes đã làm trong quá khứ."""
    async with AsyncSessionLocal() as db:
        episodes = await episode_svc.list_episodes(db, limit=limit)
        return json.dumps([
            {"id": e.id, "task_summary": e.task_summary, "outcome": e.outcome, "created_at": str(e.created_at)}
            for e in episodes
        ])


# ── MODEL ROUTING ──────────────────────────────────────────────────────────────

@mcp.tool()
async def log_model_usage(
    session_id: str,
    model_id: str,
    task_type: str,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    latency_ms: int | None = None,
    cost_usd: float | None = None,
    success: bool = True,
) -> str:
    """Ghi log hiệu suất model để Hub tự học model nào tốt cho task nào."""
    async with AsyncSessionLocal() as db:
        await model_svc.log_model_usage(db, {
            "session_id": session_id,
            "model_id": model_id,
            "task_type": task_type,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "latency_ms": latency_ms,
            "cost_usd": cost_usd,
            "success": success,
        })
        return "logged"


@mcp.tool()
async def get_model_scores(task_type: str | None = None) -> str:
    """Xem điểm hiệu suất của các model để chọn model tốt nhất cho task."""
    async with AsyncSessionLocal() as db:
        scores = await model_svc.get_model_scores(db, task_type) if task_type else []
        return json.dumps([
            {"model_id": s.model_id, "task_type": s.task_type, "final_score": s.final_score}
            for s in scores
        ])


# ── MEETING ────────────────────────────────────────────────────────────────────

@mcp.tool()
async def open_meeting(session_id: str, title: str, objective: str | None = None) -> str:
    """Mở phòng họp để Hermes điều phối nhiều AI model chuyên biệt."""
    async with AsyncSessionLocal() as db:
        room = await room_mod.open_room(db, session_id, title, objective)
        return json.dumps({"id": room.id, "title": room.title, "status": room.status})


@mcp.tool()
async def close_meeting(meeting_id: str) -> str:
    """Đóng phòng họp và lưu kết quả."""
    async with AsyncSessionLocal() as db:
        room = await room_mod.close_room(db, meeting_id)
        return json.dumps({"id": room.id, "status": room.status})


# ── Entrypoint ─────────────────────────────────────────────────────────────────

def run() -> None:
    mcp.run()


if __name__ == "__main__":
    run()

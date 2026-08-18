"""
User and session storage — aiosqlite, no ORM overhead.
"""
from __future__ import annotations

import hashlib
import json
import logging
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

import aiosqlite

from hub.config import settings

logger = logging.getLogger("xanax.database")

_VN_OFFSET = timedelta(hours=7)  # Việt Nam không có DST — offset cố định quanh năm


def _local_now() -> datetime:
    """Giờ hiện tại theo giờ Việt Nam (UTC+7) — dùng để gắn nhãn ngày/giờ cho
    usage tracking, đồng bộ với cách frontend tính ngày/tuần/tháng theo giờ địa phương."""
    return datetime.utcnow() + _VN_OFFSET

def _database_path_from_url(database_url: str) -> Path | str:
    """Chuyển URL SQLite đã cấu hình thành đường dẫn aiosqlite sử dụng trực tiếp."""
    for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
        if database_url.startswith(prefix):
            raw_path = database_url.removeprefix(prefix)
            return raw_path if raw_path == ":memory:" else Path(raw_path)
    raise ValueError("HUB_DATABASE_URL phải dùng sqlite+aiosqlite:/// hoặc sqlite:///")


DB_PATH = _database_path_from_url(settings.database_url)
SESSION_TTL_HOURS = 8  # 8 hours — force re-login after one work session
COOKIE_NAME = "xanax_session"


@asynccontextmanager
async def connect(path: Path | str | None = None):
    """Mở kết nối SQLite và chờ tối đa 5 giây khi database đang bị khóa."""
    async with aiosqlite.connect(path or DB_PATH) as db:
        # Hai pragma này thuộc về từng kết nối, nên phải đặt lại mỗi lần mở.
        await db.execute("PRAGMA busy_timeout = 5000")
        await db.execute("PRAGMA synchronous = NORMAL")
        yield db


# ── Schema ─────────────────────────────────────────────────────────────────

async def init_db() -> None:
    # Khởi tạo dùng kết nối thô: WAL là thuộc tính bền vững của file database,
    # chỉ cần đặt một lần tại đây thay vì lặp lại ở mọi connect().
    async with aiosqlite.connect(DB_PATH) as db:
        if DB_PATH != ":memory:":
            await db.execute("PRAGMA journal_mode = WAL")
        await db.execute("PRAGMA synchronous = NORMAL")
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                username     TEXT    UNIQUE NOT NULL,
                password_hash TEXT   NOT NULL,
                created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token      TEXT PRIMARY KEY,
                user_id    INTEGER NOT NULL,
                expires_at TEXT    NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS training_sessions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                title            TEXT    NOT NULL DEFAULT 'Training Session',
                task_description TEXT    NOT NULL DEFAULT '',
                status           TEXT    NOT NULL DEFAULT 'in_progress',
                result_notes     TEXT    NOT NULL DEFAULT '',
                -- Học viên của buổi dạy: đúng MỘT nhân viên, chọn lúc tạo phòng
                -- và không đổi. NULL = phiên dạy chính Xanax (toàn bộ phiên cũ).
                agent_id         INTEGER,
                -- Bài học đã chưng cất, chờ Papa duyệt trước khi ghi vào soul.
                -- Giữ trong DB thay vì chỉ trong RAM để đóng trình duyệt giữa
                -- chừng không mất bản nháp.
                lessons_json     TEXT    NOT NULL DEFAULT '',
                -- Phòng dạy đã đóng chưa. TÁCH khỏi `status`: status là kết quả
                -- đánh giá (đạt / cần cải thiện), còn đây là "buổi học kết thúc".
                -- Gộp hai thứ khiến bấm Đạt là đóng phòng ngay, không kịp sửa
                -- phần đúc kết. Chỉ nút "Lưu bài học kinh nghiệm" mới đóng.
                closed           INTEGER NOT NULL DEFAULT 0,
                created_at       TEXT    NOT NULL DEFAULT (datetime('now')),
                updated_at       TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS training_messages (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                role       TEXT    NOT NULL,
                content    TEXT    NOT NULL,
                created_at TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (session_id) REFERENCES training_sessions(id) ON DELETE CASCADE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_logs (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                task_session_id INTEGER NOT NULL,
                agent           TEXT    NOT NULL,
                type            TEXT    NOT NULL,
                content         TEXT    NOT NULL DEFAULT '',
                seq             INTEGER NOT NULL DEFAULT 0,
                created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (task_session_id) REFERENCES task_sessions(id) ON DELETE CASCADE
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS task_sessions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                title            TEXT    NOT NULL DEFAULT 'Task',
                task_description TEXT    NOT NULL DEFAULT '',
                workdir          TEXT    NOT NULL DEFAULT '',
                status           TEXT    NOT NULL DEFAULT 'in_progress',
                xanax_output     TEXT    NOT NULL DEFAULT '',
                xanax_plan_json  TEXT    NOT NULL DEFAULT '',
                claude_output    TEXT    NOT NULL DEFAULT '',
                codex_output     TEXT    NOT NULL DEFAULT '',
                result_notes     TEXT    NOT NULL DEFAULT '',
                failure_notes    TEXT    NOT NULL DEFAULT '',
                created_at       TEXT    NOT NULL DEFAULT (datetime('now')),
                updated_at       TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)
        await db.commit()
        # Migration: add xanax_plan_json for existing databases
        try:
            await db.execute(
                "ALTER TABLE task_sessions ADD COLUMN xanax_plan_json TEXT NOT NULL DEFAULT ''"
            )
            await db.commit()
        except Exception:
            pass  # column already exists
        await _run_migrations(db)
    logger.info("Database initialised at %s", DB_PATH)


# ── Password helpers ────────────────────────────────────────────────────────

def _hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key  = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
    return f"{salt}${key.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        salt, key_hex = stored.split("$", 1)
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 260_000)
        return secrets.compare_digest(key.hex(), key_hex)
    except Exception:
        return False


# ── Users ───────────────────────────────────────────────────────────────────

async def user_count() -> int:
    async with connect() as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


async def create_user(username: str, password: str) -> int:
    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (username, _hash_password(password)),
        )
        await db.commit()
        return cur.lastrowid


async def get_user_by_username(username: str) -> dict | None:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (username,),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def authenticate(username: str, password: str) -> dict | None:
    """Return user dict on success, None on failure."""
    user = await get_user_by_username(username)
    if user and _verify_password(password, user["password_hash"]):
        return {"id": user["id"], "username": user["username"]}
    return None


# ── Sessions ────────────────────────────────────────────────────────────────

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


async def create_session(user_id: int) -> str:
    token      = secrets.token_urlsafe(32)
    # Use SQLite-compatible format (space separator, no timezone suffix)
    # so that comparison with datetime('now') works correctly as string compare
    expires_at = (_now_utc() + timedelta(hours=SESSION_TTL_HOURS)).strftime('%Y-%m-%d %H:%M:%S')
    async with connect() as db:
        await db.execute(
            "INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)",
            (token, user_id, expires_at),
        )
        await db.commit()
    return token


async def validate_session(token: str) -> dict | None:
    """Return {id, username} if valid and not expired, else None."""
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT u.id, u.username
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = ?
              AND s.expires_at > datetime('now')
            """,
            (token,),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def delete_session(token: str) -> None:
    async with connect() as db:
        await db.execute("DELETE FROM sessions WHERE token = ?", (token,))
        await db.commit()


async def purge_expired_sessions() -> None:
    async with connect() as db:
        await db.execute("DELETE FROM sessions WHERE expires_at <= datetime('now')")
        await db.commit()


async def clear_all_sessions() -> None:
    """Invalidate all auth sessions — called on server startup to force re-login."""
    async with connect() as db:
        await db.execute("DELETE FROM sessions")
        await db.commit()
    logger.info("All auth sessions cleared on startup")


# ── Training sessions ────────────────────────────────────────────────────────

async def create_training_session(title: str, task_description: str = "",
                                  agent_id: int | None = None,
                                  project_id: int | None = None) -> int:
    """agent_id = học viên của buổi dạy, chọn lúc tạo và không đổi về sau.
    None = dạy chính Xanax (hành vi cũ).

    project_id = dự án của buổi dạy; quyết định bài học phạm vi "dự án" đi về soul
    dự án nào. None = buổi dạy không gắn dự án, chỉ ghi được vào nhân viên/kỹ năng.
    """
    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO training_sessions (title, task_description, agent_id, project_id) "
            "VALUES (?, ?, ?, ?)",
            (title, task_description, agent_id, project_id),
        )
        await db.commit()
        return cur.lastrowid


async def list_training_sessions() -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT s.id, s.title, s.task_description, s.status, s.result_notes, "
            "       s.agent_id, s.project_id, s.lessons_json, s.closed, "
            "       s.allowed_tools_json, s.created_at, s.updated_at, "
            "       a.name AS agent_name, a.avatar_color AS agent_avatar_color, "
            "       a.avatar_icon AS agent_avatar_icon, p.name AS project_name "
            "FROM training_sessions s "
            "LEFT JOIN agent_configs a ON a.id = s.agent_id "
            "LEFT JOIN projects p ON p.id = s.project_id "
            "ORDER BY s.created_at DESC"
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_training_session(session_id: int) -> dict | None:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT s.id, s.title, s.task_description, s.status, s.result_notes, "
            "       s.agent_id, s.project_id, s.lessons_json, s.closed, "
            "       s.allowed_tools_json, s.created_at, s.updated_at, "
            "       a.name AS agent_name, a.avatar_color AS agent_avatar_color, "
            "       a.avatar_icon AS agent_avatar_icon, p.name AS project_name "
            "FROM training_sessions s "
            "LEFT JOIN agent_configs a ON a.id = s.agent_id "
            "LEFT JOIN projects p ON p.id = s.project_id "
            "WHERE s.id = ?",
            (session_id,),
        ) as cur:
            row = await cur.fetchone()
            if row is None:
                return None
            return dict(row)


async def update_training_session(
    session_id: int,
    *,
    status: str | None = None,
    result_notes: str | None = None,
    title: str | None = None,
    task_description: str | None = None,
    lessons_json: str | None = None,
    closed: bool | None = None,
    allowed_tools_json: str | None = None,
) -> bool:
    fields, values = [], []
    if status is not None:
        fields.append("status = ?"); values.append(status)
    if result_notes is not None:
        fields.append("result_notes = ?"); values.append(result_notes)
    if title is not None:
        fields.append("title = ?"); values.append(title)
    if task_description is not None:
        fields.append("task_description = ?"); values.append(task_description)
    if lessons_json is not None:
        fields.append("lessons_json = ?"); values.append(lessons_json)
    if closed is not None:
        fields.append("closed = ?"); values.append(1 if closed else 0)
    if allowed_tools_json is not None:
        fields.append("allowed_tools_json = ?"); values.append(allowed_tools_json)
    if not fields:
        return False
    fields.append("updated_at = datetime('now')")
    values.append(session_id)
    async with connect() as db:
        cur = await db.execute(
            f"UPDATE training_sessions SET {', '.join(fields)} WHERE id = ?", values
        )
        await db.commit()
        return cur.rowcount > 0


async def delete_training_session(session_id: int) -> bool:
    async with connect() as db:
        cur = await db.execute("DELETE FROM training_sessions WHERE id = ?", (session_id,))
        await db.commit()
        return cur.rowcount > 0


# ── Training messages ────────────────────────────────────────────────────────

async def add_training_message(session_id: int, role: str, content: str) -> int:
    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO training_messages (session_id, role, content) VALUES (?, ?, ?)",
            (session_id, role, content),
        )
        await db.commit()
        return cur.lastrowid


async def get_training_messages(session_id: int) -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, session_id, role, content, created_at "
            "FROM training_messages WHERE session_id = ? ORDER BY created_at ASC",
            (session_id,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


# ── Task sessions ────────────────────────────────────────────────────────────

async def create_task_session(title: str, task_description: str, workdir: str) -> int:
    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO task_sessions (title, task_description, workdir) VALUES (?, ?, ?)",
            (title, task_description, workdir),
        )
        await db.commit()
        return cur.lastrowid


async def list_task_sessions() -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, title, task_description, workdir, status, result_notes, failure_notes, created_at, updated_at "
            "FROM task_sessions ORDER BY created_at DESC"
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def get_task_session(session_id: int) -> dict | None:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, title, task_description, workdir, status, xanax_output, xanax_plan_json, "
            "claude_output, codex_output, result_notes, failure_notes, created_at, updated_at "
            "FROM task_sessions WHERE id = ?",
            (session_id,),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def update_task_session(
    session_id: int,
    *,
    status: str | None = None,
    xanax_output: str | None = None,
    xanax_plan_json: str | None = None,
    claude_output: str | None = None,
    codex_output: str | None = None,
    result_notes: str | None = None,
    failure_notes: str | None = None,
    title: str | None = None,
) -> bool:
    fields, values = [], []
    if status is not None:
        fields.append("status = ?"); values.append(status)
    if xanax_output is not None:
        fields.append("xanax_output = ?"); values.append(xanax_output)
    if xanax_plan_json is not None:
        fields.append("xanax_plan_json = ?"); values.append(xanax_plan_json)
    if claude_output is not None:
        fields.append("claude_output = ?"); values.append(claude_output)
    if codex_output is not None:
        fields.append("codex_output = ?"); values.append(codex_output)
    if result_notes is not None:
        fields.append("result_notes = ?"); values.append(result_notes)
    if failure_notes is not None:
        fields.append("failure_notes = ?"); values.append(failure_notes)
    if title is not None:
        fields.append("title = ?"); values.append(title)
    if not fields:
        return False
    fields.append("updated_at = datetime('now')")
    values.append(session_id)
    async with connect() as db:
        cur = await db.execute(
            f"UPDATE task_sessions SET {', '.join(fields)} WHERE id = ?", values
        )
        await db.commit()
        return cur.rowcount > 0


async def add_pipeline_log(task_session_id: int, agent: str, type_: str, content: str, seq: int = 0) -> None:
    async with connect() as db:
        await db.execute(
            "INSERT INTO pipeline_logs (task_session_id, agent, type, content, seq) VALUES (?, ?, ?, ?, ?)",
            (task_session_id, agent, type_, content, seq),
        )
        await db.commit()


async def get_pipeline_logs(task_session_id: int) -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT agent, type, content FROM pipeline_logs "
            "WHERE task_session_id = ? ORDER BY seq ASC, id ASC",
            (task_session_id,),
        ) as cur:
            rows = await cur.fetchall()
            return [dict(r) for r in rows]


async def delete_agent_pipeline_logs(task_session_id: int, agent: str) -> None:
    async with connect() as db:
        await db.execute(
            "DELETE FROM pipeline_logs WHERE task_session_id = ? AND agent = ?",
            (task_session_id, agent),
        )
        await db.commit()


async def delete_task_session(session_id: int) -> bool:
    async with connect() as db:
        cur = await db.execute("DELETE FROM task_sessions WHERE id = ?", (session_id,))
        await db.commit()
        return cur.rowcount > 0


# ── Agent Configs ────────────────────────────────────────────────────────────

async def _run_migrations(db) -> None:
    """Add new tables if they don't exist (safe to run multiple times)."""
    await db.execute("""
        CREATE TABLE IF NOT EXISTS departments (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            description TEXT    NOT NULL DEFAULT '',
            color       TEXT    NOT NULL DEFAULT '#9366ff',
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS agent_configs (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT    NOT NULL,
            role          TEXT    NOT NULL DEFAULT 'Assistant',
            model         TEXT    NOT NULL DEFAULT '',
            system_prompt TEXT    NOT NULL DEFAULT '',
            avatar_color  TEXT    NOT NULL DEFAULT '#9366ff',
            skills_json   TEXT    NOT NULL DEFAULT '[]',
            enabled       INTEGER NOT NULL DEFAULT 1,
            created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at    TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS skills (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT    NOT NULL UNIQUE,
            description  TEXT    NOT NULL DEFAULT '',
            type         TEXT    NOT NULL DEFAULT 'builtin',
            config_json  TEXT    NOT NULL DEFAULT '{}',
            enabled      INTEGER NOT NULL DEFAULT 1,
            created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            name        TEXT    NOT NULL,
            description TEXT    NOT NULL DEFAULT '',
            status      TEXT    NOT NULL DEFAULT 'active',
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS work_items (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id        INTEGER NOT NULL,
            title             TEXT    NOT NULL,
            description       TEXT    NOT NULL DEFAULT '',
            status            TEXT    NOT NULL DEFAULT 'backlog',
            priority          TEXT    NOT NULL DEFAULT 'medium',
            assigned_agent_id INTEGER,
            created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at        TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
            FOREIGN KEY (assigned_agent_id) REFERENCES agent_configs(id) ON DELETE SET NULL
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS meetings (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            title             TEXT    NOT NULL,
            topic             TEXT    NOT NULL DEFAULT '',
            status            TEXT    NOT NULL DEFAULT 'active',
            participants_json TEXT    NOT NULL DEFAULT '[]',
            created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
            ended_at          TEXT
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS meeting_messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            meeting_id  INTEGER NOT NULL,
            sender      TEXT    NOT NULL,
            sender_type TEXT    NOT NULL DEFAULT 'agent',
            content     TEXT    NOT NULL,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (meeting_id) REFERENCES meetings(id) ON DELETE CASCADE
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS benchmarks (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT    NOT NULL,
            role_description TEXT    NOT NULL DEFAULT '',
            test_cases_json  TEXT    NOT NULL DEFAULT '[]',
            models_json      TEXT    NOT NULL DEFAULT '[]',
            status           TEXT    NOT NULL DEFAULT 'pending',
            created_at       TEXT    NOT NULL DEFAULT (datetime('now')),
            completed_at     TEXT
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS benchmark_results (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            benchmark_id INTEGER NOT NULL,
            model        TEXT    NOT NULL,
            scores_json  TEXT    NOT NULL DEFAULT '{}',
            responses_json TEXT  NOT NULL DEFAULT '[]',
            recommendation TEXT  NOT NULL DEFAULT '',
            created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (benchmark_id) REFERENCES benchmarks(id) ON DELETE CASCADE
        )
    """)
    # Bộ thí nghiệm ablation tự cải thiện. Tách khỏi benchmarks vì đơn vị so
    # sánh ở đây là điều kiện tri thức, không phải tên model.
    await db.execute("""
        CREATE TABLE IF NOT EXISTS experiments (
            id                     INTEGER PRIMARY KEY AUTOINCREMENT,
            name                   TEXT    NOT NULL,
            agent_id               INTEGER NOT NULL,
            project_id             INTEGER,
            benchmark_id           INTEGER NOT NULL,
            measured_model_pool_id INTEGER NOT NULL,
            judge_model_pool_id    INTEGER NOT NULL,
            repetitions            INTEGER NOT NULL DEFAULT 3,
            status                 TEXT    NOT NULL DEFAULT 'pending',
            total_trials           INTEGER NOT NULL DEFAULT 0,
            completed_trials       INTEGER NOT NULL DEFAULT 0,
            scored_trials          INTEGER NOT NULL DEFAULT 0,
            warnings_json          TEXT    NOT NULL DEFAULT '[]',
            config_snapshot_json   TEXT    NOT NULL DEFAULT '{}',
            soul_snapshot_json     TEXT    NOT NULL DEFAULT '{}',
            error_text             TEXT    NOT NULL DEFAULT '',
            created_at             TEXT    NOT NULL DEFAULT (datetime('now')),
            started_at             TEXT,
            completed_at           TEXT,
            updated_at             TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (agent_id) REFERENCES agent_configs(id),
            FOREIGN KEY (project_id) REFERENCES projects(id),
            FOREIGN KEY (benchmark_id) REFERENCES benchmarks(id),
            FOREIGN KEY (measured_model_pool_id) REFERENCES model_pool(id),
            FOREIGN KEY (judge_model_pool_id) REFERENCES model_pool(id)
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS experiment_judgements (
            id                 INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id      INTEGER NOT NULL,
            case_index         INTEGER NOT NULL,
            judge_model_pool_id INTEGER NOT NULL,
            item_map_json      TEXT    NOT NULL DEFAULT '{}',
            judge_prompt       TEXT    NOT NULL DEFAULT '',
            raw_response       TEXT    NOT NULL DEFAULT '',
            status             TEXT    NOT NULL DEFAULT 'pending',
            error_text         TEXT    NOT NULL DEFAULT '',
            elapsed_seconds    REAL    NOT NULL DEFAULT 0,
            tokens_input       INTEGER NOT NULL DEFAULT 0,
            tokens_cache       INTEGER NOT NULL DEFAULT 0,
            tokens_output      INTEGER NOT NULL DEFAULT 0,
            created_at         TEXT    NOT NULL DEFAULT (datetime('now')),
            completed_at       TEXT,
            FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS experiment_trials (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            experiment_id     INTEGER NOT NULL,
            condition         TEXT    NOT NULL,
            case_index        INTEGER NOT NULL,
            repetition        INTEGER NOT NULL,
            execution_order   INTEGER NOT NULL,
            judge_order       INTEGER,
            prompt            TEXT    NOT NULL,
            criteria          TEXT    NOT NULL DEFAULT '',
            response          TEXT    NOT NULL DEFAULT '',
            score             REAL,
            score_reason      TEXT    NOT NULL DEFAULT '',
            response_classification TEXT NOT NULL DEFAULT 'answered',
            status            TEXT    NOT NULL DEFAULT 'pending',
            error_text        TEXT    NOT NULL DEFAULT '',
            elapsed_seconds   REAL    NOT NULL DEFAULT 0,
            tokens_input      INTEGER NOT NULL DEFAULT 0,
            tokens_cache      INTEGER NOT NULL DEFAULT 0,
            tokens_output     INTEGER NOT NULL DEFAULT 0,
            judgement_id      INTEGER,
            created_at        TEXT    NOT NULL DEFAULT (datetime('now')),
            started_at        TEXT,
            completed_at      TEXT,
            FOREIGN KEY (experiment_id) REFERENCES experiments(id) ON DELETE CASCADE,
            FOREIGN KEY (judgement_id) REFERENCES experiment_judgements(id),
            UNIQUE(experiment_id, condition, case_index, repetition)
        )
    """)
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_experiment_trials_run ON experiment_trials(experiment_id, execution_order)"
    )
    await db.execute(
        "CREATE INDEX IF NOT EXISTS idx_experiment_trials_summary ON experiment_trials(experiment_id, condition, score)"
    )
    await db.execute("""
        CREATE TABLE IF NOT EXISTS task_alerts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            work_item_id    INTEGER NOT NULL,
            project_id      INTEGER NOT NULL,
            title           TEXT    NOT NULL DEFAULT '',
            reason          TEXT    NOT NULL DEFAULT 'no_matching_agent',
            status          TEXT    NOT NULL DEFAULT 'open',
            suggestions_json TEXT   NOT NULL DEFAULT '[]',
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            resolved_at     TEXT,
            FOREIGN KEY (work_item_id) REFERENCES work_items(id) ON DELETE CASCADE
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS workflow_tasks (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT    NOT NULL,
            kind             TEXT    NOT NULL DEFAULT 'automation',
            description      TEXT    NOT NULL DEFAULT '',
            project_id       INTEGER,
            agents_json      TEXT    NOT NULL DEFAULT '[]',
            graph_json       TEXT    NOT NULL DEFAULT '',
            trigger_type     TEXT    NOT NULL DEFAULT 'manual',
            trigger_config_json TEXT NOT NULL DEFAULT '{}',
            schedule_enabled INTEGER NOT NULL DEFAULT 0,
            schedule_cron    TEXT    NOT NULL DEFAULT '',
            status           TEXT    NOT NULL DEFAULT 'active',
            created_at       TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at       TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS workflow_runs (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id      INTEGER NOT NULL,
            project_id   INTEGER,
            task_name    TEXT    NOT NULL DEFAULT '',
            status       TEXT    NOT NULL DEFAULT 'pending',
            triggered_by TEXT    NOT NULL DEFAULT 'manual',
            started_at   TEXT,
            completed_at TEXT,
            review_status TEXT   NOT NULL DEFAULT 'waiting_review',
            priority     TEXT    NOT NULL DEFAULT 'medium',
            output_type  TEXT    NOT NULL DEFAULT 'text',
            feedback     TEXT,
            ready_for_next INTEGER NOT NULL DEFAULT 0,
            reviewed_at  TEXT,
            archive_payload_json TEXT,
            last_action_test INTEGER NOT NULL DEFAULT 0,
            created_at   TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (task_id) REFERENCES workflow_tasks(id) ON DELETE CASCADE
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS workflow_outputs (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id          INTEGER NOT NULL,
            task_id         INTEGER NOT NULL,
            agent_id        INTEGER,
            agent_name      TEXT    NOT NULL DEFAULT '',
            step_order      INTEGER NOT NULL DEFAULT 0,
            output_content  TEXT    NOT NULL DEFAULT '',
            status          TEXT    NOT NULL DEFAULT 'pending',
            pass_fail       TEXT,
            edited_content  TEXT,
            notes           TEXT    NOT NULL DEFAULT '',
            tokens_input    INTEGER NOT NULL DEFAULT 0,
            tokens_output   INTEGER NOT NULL DEFAULT 0,
            created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (run_id) REFERENCES workflow_runs(id) ON DELETE CASCADE
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS model_pool (
            id                   INTEGER PRIMARY KEY AUTOINCREMENT,
            name                 TEXT    NOT NULL,
            provider             TEXT    NOT NULL DEFAULT '9router',
            api_style            TEXT    NOT NULL DEFAULT 'openai_compat',
            model_id             TEXT    NOT NULL,
            base_url             TEXT    NOT NULL DEFAULT '',
            api_key              TEXT    NOT NULL DEFAULT '',
            cli_config_dir       TEXT    NOT NULL DEFAULT '',
            category             TEXT    NOT NULL DEFAULT 'general',
            max_requests_per_day INTEGER NOT NULL DEFAULT 0,
            max_tokens_per_day   INTEGER NOT NULL DEFAULT 0,
            price_input_per_1m   REAL    NOT NULL DEFAULT 0,
            price_cache_per_1m   REAL    NOT NULL DEFAULT 0,
            price_output_per_1m  REAL    NOT NULL DEFAULT 0,
            currency             TEXT    NOT NULL DEFAULT 'USD',
            enabled              INTEGER NOT NULL DEFAULT 1,
            created_at           TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS assets (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            filename     TEXT    NOT NULL,
            stored_path  TEXT    NOT NULL,
            mime_type    TEXT    NOT NULL DEFAULT '',
            size_bytes   INTEGER NOT NULL DEFAULT 0,
            source       TEXT    NOT NULL DEFAULT 'upload',
            note         TEXT    NOT NULL DEFAULT '',
            created_at   TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_documents (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id  INTEGER,
            title       TEXT    NOT NULL,
            content     TEXT    NOT NULL DEFAULT '',
            tags        TEXT    NOT NULL DEFAULT '',
            created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS model_usage (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            model_pool_id  INTEGER NOT NULL,
            date           TEXT    NOT NULL,
            request_count  INTEGER NOT NULL DEFAULT 0,
            tokens_input   INTEGER NOT NULL DEFAULT 0,
            tokens_cache   INTEGER NOT NULL DEFAULT 0,
            tokens_output  INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (model_pool_id) REFERENCES model_pool(id) ON DELETE CASCADE,
            UNIQUE(model_pool_id, date)
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS model_usage_hourly (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            model_pool_id  INTEGER NOT NULL,
            date           TEXT    NOT NULL,
            hour           INTEGER NOT NULL,
            request_count  INTEGER NOT NULL DEFAULT 0,
            tokens_input   INTEGER NOT NULL DEFAULT 0,
            tokens_cache   INTEGER NOT NULL DEFAULT 0,
            tokens_output  INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (model_pool_id) REFERENCES model_pool(id) ON DELETE CASCADE,
            UNIQUE(model_pool_id, date, hour)
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS model_call_log (
            id             INTEGER PRIMARY KEY AUTOINCREMENT,
            model_pool_id  INTEGER NOT NULL,
            called_at      TEXT    NOT NULL,
            tokens_input   INTEGER NOT NULL DEFAULT 0,
            tokens_cache   INTEGER NOT NULL DEFAULT 0,
            tokens_output  INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (model_pool_id) REFERENCES model_pool(id) ON DELETE CASCADE
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS xanax_notes (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            content    TEXT    NOT NULL,
            created_at TEXT    NOT NULL DEFAULT (datetime('now'))
        )
    """)
    await db.execute("""
        CREATE TABLE IF NOT EXISTS ops_history (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER NOT NULL,
            output_id  INTEGER,
            run_id     INTEGER,
            type       TEXT    NOT NULL,
            text       TEXT    NOT NULL,
            created_at TEXT    NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (output_id) REFERENCES workflow_outputs(id) ON DELETE CASCADE,
            FOREIGN KEY (run_id) REFERENCES workflow_runs(id) ON DELETE CASCADE
        )
    """)
    await db.commit()
    # Migrations: add match columns to work_items if not exist
    for col_sql in [
        "ALTER TABLE work_items ADD COLUMN match_score REAL NOT NULL DEFAULT 0.0",
        "ALTER TABLE work_items ADD COLUMN match_reason TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE agent_configs ADD COLUMN model_pool_id INTEGER",
        "ALTER TABLE agent_configs ADD COLUMN model_pool_ids_json TEXT NOT NULL DEFAULT '[]'",
        "ALTER TABLE agent_configs ADD COLUMN avatar_icon TEXT NOT NULL DEFAULT 'bot'",
        # Chọn lẻ công cụ bên trong một skill MCP: {"<skill_id>": ["cut_product"]}.
        # Vắng mặt hoặc danh sách rỗng = lấy hết công cụ của skill đó, nên nhân viên
        # cũ không đổi hành vi (xem core/mcp_client.parse_skill_tools).
        "ALTER TABLE agent_configs ADD COLUMN skill_tools_json TEXT NOT NULL DEFAULT '{}'",
        # Công cụ học viên được phép dùng trong ĐÚNG buổi dạy này. Mặc định rỗng =
        # không có công cụ nào, giữ nguyên hành vi cũ. Cấp theo từng buổi chứ không
        # theo nhân viên: một buổi dạy cắt ảnh không có lý do gì được cầm luôn
        # công cụ đăng bài của cùng nhân viên đó.
        "ALTER TABLE training_sessions ADD COLUMN allowed_tools_json TEXT NOT NULL DEFAULT '[]'",
        "ALTER TABLE workflow_tasks ADD COLUMN graph_json TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE workflow_tasks ADD COLUMN trigger_type TEXT NOT NULL DEFAULT 'manual'",
        "ALTER TABLE workflow_tasks ADD COLUMN trigger_config_json TEXT NOT NULL DEFAULT '{}'",
        "ALTER TABLE workflow_tasks ADD COLUMN kind TEXT NOT NULL DEFAULT 'automation'",
        "ALTER TABLE workflow_outputs ADD COLUMN tokens_input INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE workflow_outputs ADD COLUMN tokens_output INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE model_pool ADD COLUMN price_input_per_1m REAL NOT NULL DEFAULT 0",
        "ALTER TABLE model_pool ADD COLUMN price_output_per_1m REAL NOT NULL DEFAULT 0",
        "ALTER TABLE model_pool ADD COLUMN currency TEXT NOT NULL DEFAULT 'USD'",
        "ALTER TABLE meetings ADD COLUMN decision_text TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE meetings ADD COLUMN decided_at TEXT",
        "ALTER TABLE meetings ADD COLUMN project_id INTEGER",
        # Cuộc họp đã kích hoạt lần chạy — để mở lại phòng họp là thấy lại các
        # cửa duyệt còn đang chờ (xem list_pending_approvals).
        "ALTER TABLE workflow_runs ADD COLUMN meeting_id INTEGER",
        # Project Ops Dashboard (Overview/Runs/Review Queue/Kanban/History) — mỗi
        # workflow_outputs = 1 "item" trên bảng ops; review_status là vòng đời
        # duyệt của CEO, tách biệt với status kỹ thuật (running/done/error) ở trên.
        "ALTER TABLE workflow_outputs ADD COLUMN review_status TEXT NOT NULL DEFAULT 'waiting_review'",
        "ALTER TABLE workflow_outputs ADD COLUMN priority TEXT NOT NULL DEFAULT 'medium'",
        "ALTER TABLE workflow_outputs ADD COLUMN output_type TEXT NOT NULL DEFAULT 'text'",
        "ALTER TABLE workflow_outputs ADD COLUMN feedback TEXT",
        "ALTER TABLE workflow_outputs ADD COLUMN ready_for_next INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE workflow_outputs ADD COLUMN reviewed_at TEXT",
        "ALTER TABLE workflow_outputs ADD COLUMN archive_payload_json TEXT",
        "ALTER TABLE workflow_outputs ADD COLUMN finished_at TEXT",
        "ALTER TABLE workflow_outputs ADD COLUMN last_action_test INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE workflow_runs ADD COLUMN review_status TEXT NOT NULL DEFAULT 'waiting_review'",
        "ALTER TABLE workflow_runs ADD COLUMN priority TEXT NOT NULL DEFAULT 'medium'",
        "ALTER TABLE workflow_runs ADD COLUMN output_type TEXT NOT NULL DEFAULT 'text'",
        "ALTER TABLE workflow_runs ADD COLUMN feedback TEXT",
        "ALTER TABLE workflow_runs ADD COLUMN ready_for_next INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE workflow_runs ADD COLUMN reviewed_at TEXT",
        "ALTER TABLE workflow_runs ADD COLUMN archive_payload_json TEXT",
        "ALTER TABLE workflow_runs ADD COLUMN last_action_test INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE ops_history ADD COLUMN run_id INTEGER",
        "ALTER TABLE model_pool ADD COLUMN api_style TEXT NOT NULL DEFAULT 'openai_compat'",
        # Model chạy qua CLI (api_style claude_cli/codex_cli) không dùng base_url/api_key.
        # Thay vào đó nó cần thư mục tài khoản của CLI — mỗi gói thuê bao một thư mục,
        # đó là cách chạy nhiều tài khoản song song trên cùng một máy.
        # Để trống = dùng tài khoản mặc định (~/.claude, ~/.codex).
        "ALTER TABLE model_pool ADD COLUMN cli_config_dir TEXT NOT NULL DEFAULT ''",
        "ALTER TABLE model_pool ADD COLUMN price_cache_per_1m REAL NOT NULL DEFAULT 0",
        "ALTER TABLE model_usage ADD COLUMN tokens_cache INTEGER NOT NULL DEFAULT 0",
        # Slug cố định để đặt tên folder lưu trữ kết quả quy trình theo dự án
        # (core/project_storage.py) — sinh 1 lần lúc tạo, không đổi khi rename.
        "ALTER TABLE projects ADD COLUMN slug TEXT",
        "ALTER TABLE workflow_tasks ADD COLUMN slug TEXT",
        # Phòng ban — nhóm nhân viên AI, chuẩn bị cho tính năng họp theo phòng ban
        "ALTER TABLE agent_configs ADD COLUMN department_id INTEGER",
        "ALTER TABLE departments ADD COLUMN head_agent_id INTEGER",
        # Phòng dạy AI gắn với đúng 1 nhân viên học viên (NULL = dạy chính Xanax,
        # là toàn bộ phiên có từ trước). lessons_json giữ bản nháp bài học đã
        # chưng cất, chờ Papa duyệt rồi mới ghi vào soul của nhân viên đó.
        "ALTER TABLE training_sessions ADD COLUMN agent_id INTEGER",
        "ALTER TABLE training_sessions ADD COLUMN lessons_json TEXT NOT NULL DEFAULT ''",
        # Dự án của buổi dạy (NULL = dạy chung, không gắn thương hiệu nào). Có nó
        # thì bài học về giọng thương hiệu mới biết đường về soul dự án thay vì
        # bị nhét vào soul nhân viên rồi theo nhân viên đó sang dự án khác.
        "ALTER TABLE training_sessions ADD COLUMN project_id INTEGER",
        # (cột `closed` được thêm trong _backfill_closed_sessions, xem lý do ở đó)
        # Biên bản nháp Xanax tự tổng hợp khi kết thúc họp — CEO xem/sửa rồi mới chốt
        # (decision_text/decided_at) qua endpoint finalize hiện có.
        "ALTER TABLE meetings ADD COLUMN draft_minutes TEXT NOT NULL DEFAULT ''",
        # Các đầu việc Xanax tách từ biên bản đã chốt, chờ CEO duyệt trước khi
        # thực sự tạo work_items trong dự án liên kết.
        "ALTER TABLE meetings ADD COLUMN proposed_items_json TEXT NOT NULL DEFAULT '[]'",
        # Dữ liệu thí nghiệm cũ chưa có phân loại nên mặc định answered. Đây là
        # lựa chọn tương thích: không được tự suy diễn lại hành vi từ câu chữ cũ.
        "ALTER TABLE experiment_trials ADD COLUMN response_classification TEXT NOT NULL DEFAULT 'answered'",
    ]:
        try:
            await db.execute(col_sql)
            await db.commit()
        except Exception:
            pass  # column already exists

    # Cột đã bị gỡ khỏi thiết kế — dọn khỏi các DB cũ. Nhân viên dùng đúng model
    # được cấp cho mọi thao tác (text hay ảnh), không còn phân loại modality nữa.
    for col_sql in [
        "ALTER TABLE model_pool DROP COLUMN modality",
    ]:
        try:
            await db.execute(col_sql)
            await db.commit()
        except Exception:
            pass  # column already dropped (hoặc SQLite < 3.35)

    await _backfill_closed_sessions(db)

    await _backfill_slugs(db, "projects", fallback="du-an")
    await _backfill_slugs(db, "workflow_tasks", fallback="quy-trinh")


async def _backfill_closed_sessions(db) -> None:
    """Thêm cột `closed` cho training_sessions và backfill ĐÚNG MỘT LẦN.

    Không để chung với danh sách ALTER phía trên vì vòng lặp đó chạy lại mỗi
    lần khởi động và nuốt lỗi. Một câu `UPDATE ... SET closed = 1 WHERE status
    IN ('pass','fail')` đặt ở đó sẽ đóng lại đúng những phiên Papa vừa mở ra
    sửa — hỏng âm thầm, và chỉ lộ ra sau lần restart kế tiếp.

    Ở đây điều kiện chạy là "cột chưa tồn tại", nên backfill gắn liền với lần
    tạo cột và không bao giờ lặp lại.
    """
    async with db.execute("PRAGMA table_info(training_sessions)") as cur:
        cols = {r[1] for r in await cur.fetchall()}
    if "closed" in cols:
        return

    await db.execute(
        "ALTER TABLE training_sessions ADD COLUMN closed INTEGER NOT NULL DEFAULT 0"
    )
    # Phiên cũ đã có kết quả đánh giá thì theo luật cũ là đã đóng — giữ nguyên
    # vẻ ngoài của chúng thay vì bỗng dưng mở lại hết.
    await db.execute(
        "UPDATE training_sessions SET closed = 1 WHERE status IN ('pass', 'fail')"
    )
    await db.commit()
    logger.info("training_sessions: đã thêm cột `closed` và backfill phiên cũ")


async def _backfill_slugs(db, table: str, *, fallback: str) -> None:
    """Sinh slug cho các dòng cũ chưa có slug (tạo trước khi thêm cột này)."""
    from core.slugify import slugify

    async with db.execute(f"SELECT id, name FROM {table} WHERE slug IS NULL OR slug = ''") as cur:
        rows = await cur.fetchall()
    for row_id, name in rows:
        base_slug = slugify(name, fallback=fallback)
        slug = await _unique_slug(db, table, base_slug)
        await db.execute(f"UPDATE {table} SET slug = ? WHERE id = ?", (slug, row_id))
    if rows:
        await db.commit()


async def _unique_slug(db, table: str, base_slug: str) -> str:
    """Trả về 1 slug chưa tồn tại trong `table`, thêm hậu tố -2, -3... nếu trùng."""
    slug = base_slug
    n = 2
    while True:
        async with db.execute(f"SELECT id FROM {table} WHERE slug = ?", (slug,)) as cur:
            if not await cur.fetchone():
                return slug
        slug = f"{base_slug}-{n}"
        n += 1


# ── Departments (phòng ban) ───────────────────────────────────────────────────

async def list_departments() -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT d.*, COUNT(a.id) AS agent_count,
                      h.name AS head_agent_name, h.avatar_color AS head_agent_color
               FROM departments d
               LEFT JOIN agent_configs a ON a.department_id = d.id
               LEFT JOIN agent_configs h ON h.id = d.head_agent_id
               GROUP BY d.id
               ORDER BY d.created_at ASC"""
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_department(department_id: int) -> dict | None:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT d.*, h.name AS head_agent_name, h.avatar_color AS head_agent_color
               FROM departments d
               LEFT JOIN agent_configs h ON h.id = d.head_agent_id
               WHERE d.id = ?""",
            (department_id,),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def create_department(
    name: str, description: str = "", color: str = "#9366ff", head_agent_id: int | None = None,
) -> int:
    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO departments (name,description,color,head_agent_id) VALUES (?,?,?,?)",
            (name, description, color, head_agent_id),
        )
        await db.commit()
        return cur.lastrowid


async def update_department(department_id: int, **kwargs) -> bool:
    allowed = {"name", "description", "color", "head_agent_id"}
    nullable = {"head_agent_id"}  # được phép set về None để gỡ trưởng phòng
    fields, values = [], []
    for k, v in kwargs.items():
        if k not in allowed:
            continue
        if v is None and k not in nullable:
            continue
        fields.append(f"{k} = ?")
        values.append(v)
    if not fields:
        return False
    fields.append("updated_at = datetime('now')")
    values.append(department_id)
    async with connect() as db:
        cur = await db.execute(
            f"UPDATE departments SET {', '.join(fields)} WHERE id = ?", values
        )
        await db.commit()
        return cur.rowcount > 0


async def delete_department(department_id: int) -> bool:
    async with connect() as db:
        await db.execute(
            "UPDATE agent_configs SET department_id = NULL WHERE department_id = ?", (department_id,)
        )
        cur = await db.execute("DELETE FROM departments WHERE id = ?", (department_id,))
        await db.commit()
        return cur.rowcount > 0


async def list_agent_configs() -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT a.*, mp.model_id AS pool_model_id, mp.name AS pool_name,
                      d.name AS department_name, d.color AS department_color
               FROM agent_configs a
               LEFT JOIN model_pool mp ON mp.id = a.model_pool_id
               LEFT JOIN departments d ON d.id = a.department_id
               ORDER BY a.created_at ASC"""
        ) as cur:
            rows = [dict(r) for r in await cur.fetchall()]
    # Derive model string from pool entry when model_pool_id is set
    for r in rows:
        if r.get("model_pool_id") and r.get("pool_model_id"):
            r["model"] = r["pool_model_id"]
        r.pop("pool_model_id", None)
        r.pop("pool_name", None)
        _migrate_model_pool_ids_row(r)
    return rows


def _migrate_model_pool_ids_row(row: dict) -> dict:
    """Nếu chưa có danh sách model ưu tiên (model_pool_ids_json) mà vẫn còn
    model_pool_id đơn (dữ liệu cũ) thì suy ra danh sách 1 phần tử — giữ tương
    thích ngược, không cần script migrate hàng loạt."""
    try:
        ids = json.loads(row.get("model_pool_ids_json") or "[]")
    except Exception:
        ids = []
    if not ids and row.get("model_pool_id"):
        ids = [row["model_pool_id"]]
    row["model_pool_ids_json"] = json.dumps(ids)
    return row


async def get_agent_config(agent_id: int) -> dict | None:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT a.*, d.name AS department_name, d.color AS department_color
               FROM agent_configs a
               LEFT JOIN departments d ON d.id = a.department_id
               WHERE a.id = ?""",
            (agent_id,),
        ) as cur:
            row = await cur.fetchone()
            return _migrate_model_pool_ids_row(dict(row)) if row else None


async def get_agent_configs_by_ids(ids: list[int]) -> list[dict]:
    if not ids:
        return []
    placeholders = ",".join("?" * len(ids))
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"""SELECT a.*, mp.model_id AS pool_model_id, mp.name AS pool_name,
                       d.name AS department_name, d.color AS department_color
                FROM agent_configs a
                LEFT JOIN model_pool mp ON mp.id = a.model_pool_id
                LEFT JOIN departments d ON d.id = a.department_id
                WHERE a.id IN ({placeholders})""",
            ids,
        ) as cur:
            rows = [dict(r) for r in await cur.fetchall()]
    # Derive model string from pool entry + migrate model_pool_ids_json, giống list_agent_configs —
    # thiếu bước này khiến phòng họp gọi sai model (không theo danh sách ưu tiên đã cấu hình).
    for r in rows:
        if r.get("model_pool_id") and r.get("pool_model_id"):
            r["model"] = r["pool_model_id"]
        r.pop("pool_model_id", None)
        r.pop("pool_name", None)
        _migrate_model_pool_ids_row(r)
    return rows


async def create_agent_config(
    name: str, role: str = "Assistant", model: str = "",
    system_prompt: str = "", avatar_color: str = "#9366ff", avatar_icon: str = "bot",
    skills_json: str = "[]",
    model_pool_id: int | None = None, model_pool_ids_json: str = "[]",
    department_id: int | None = None, skill_tools_json: str = "{}",
) -> int:
    async with connect() as db:
        cur = await db.execute(
            """INSERT INTO agent_configs
               (name,role,model,system_prompt,avatar_color,avatar_icon,skills_json,model_pool_id,model_pool_ids_json,department_id,skill_tools_json)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (name, role, model, system_prompt, avatar_color, avatar_icon, skills_json, model_pool_id,
             model_pool_ids_json, department_id, skill_tools_json),
        )
        await db.commit()
        return cur.lastrowid


async def update_agent_config(agent_id: int, **kwargs) -> bool:
    allowed = {"name", "role", "model", "system_prompt", "avatar_color", "avatar_icon", "skills_json", "enabled",
               "model_pool_id", "model_pool_ids_json", "department_id", "skill_tools_json"}
    nullable = {"model_pool_id", "department_id"}  # được phép set về None để gỡ liên kết
    fields, values = [], []
    for k, v in kwargs.items():
        if k not in allowed:
            continue
        if v is None and k not in nullable:
            continue
        fields.append(f"{k} = ?")
        values.append(v)
    if not fields:
        return False
    fields.append("updated_at = datetime('now')")
    values.append(agent_id)
    async with connect() as db:
        cur = await db.execute(
            f"UPDATE agent_configs SET {', '.join(fields)} WHERE id = ?", values
        )
        await db.commit()
        return cur.rowcount > 0


async def delete_agent_config(agent_id: int) -> bool:
    async with connect() as db:
        # head_agent_id được thêm bằng ALTER TABLE nên không có FK ON DELETE SET NULL —
        # phải tự gỡ chỉ định trưởng phòng ở đây, nếu không phòng ban vẫn trỏ tới 1 agent_id
        # đã xoá, khiến UI tưởng phòng đã có trưởng phòng (ẩn mất mục "Đặt làm Trưởng phòng").
        await db.execute("UPDATE departments SET head_agent_id = NULL WHERE head_agent_id = ?", (agent_id,))
        cur = await db.execute("DELETE FROM agent_configs WHERE id = ?", (agent_id,))
        await db.commit()
        return cur.rowcount > 0


# ── Skills ───────────────────────────────────────────────────────────────────

async def list_skills() -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM skills ORDER BY name ASC") as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_skill(skill_id: int) -> dict | None:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM skills WHERE id = ?", (skill_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def create_skill(name: str, description: str = "", type_: str = "builtin",
                       config_json: str = "{}") -> int:
    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO skills (name,description,type,config_json) VALUES (?,?,?,?)",
            (name, description, type_, config_json),
        )
        await db.commit()
        return cur.lastrowid


async def update_skill(skill_id: int, **kwargs) -> bool:
    allowed = {"name", "description", "type", "config_json", "enabled"}
    fields, values = [], []
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        return False
    values.append(skill_id)
    async with connect() as db:
        cur = await db.execute(
            f"UPDATE skills SET {', '.join(fields)} WHERE id = ?", values
        )
        await db.commit()
        return cur.rowcount > 0


async def delete_skill(skill_id: int) -> bool:
    async with connect() as db:
        cur = await db.execute("DELETE FROM skills WHERE id = ?", (skill_id,))
        await db.commit()
        return cur.rowcount > 0


# ── Projects ─────────────────────────────────────────────────────────────────

async def list_projects() -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM projects ORDER BY created_at DESC") as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_project(project_id: int) -> dict | None:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM projects WHERE id = ?", (project_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def create_project(name: str, description: str = "") -> int:
    from core.slugify import slugify

    async with connect() as db:
        slug = await _unique_slug(db, "projects", slugify(name, fallback="du-an"))
        cur = await db.execute(
            "INSERT INTO projects (name,description,slug) VALUES (?,?,?)", (name, description, slug)
        )
        await db.commit()
        return cur.lastrowid


async def update_project(project_id: int, **kwargs) -> bool:
    allowed = {"name", "description", "status"}
    fields, values = [], []
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        return False
    fields.append("updated_at = datetime('now')")
    values.append(project_id)
    async with connect() as db:
        cur = await db.execute(
            f"UPDATE projects SET {', '.join(fields)} WHERE id = ?", values
        )
        await db.commit()
        return cur.rowcount > 0


async def delete_project(project_id: int) -> bool:
    async with connect() as db:
        cur = await db.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        await db.commit()
        return cur.rowcount > 0


# ── Work Items ───────────────────────────────────────────────────────────────

async def list_work_items(project_id: int) -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT w.*, a.name as agent_name, a.avatar_color as agent_color "
            "FROM work_items w LEFT JOIN agent_configs a ON a.id = w.assigned_agent_id "
            "WHERE w.project_id = ? ORDER BY w.created_at ASC",
            (project_id,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_work_item(item_id: int) -> dict | None:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT w.*, a.name as agent_name, a.avatar_color as agent_color "
            "FROM work_items w LEFT JOIN agent_configs a ON a.id = w.assigned_agent_id "
            "WHERE w.id = ?",
            (item_id,),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def create_work_item(project_id: int, title: str, description: str = "",
                           status: str = "backlog", priority: str = "medium",
                           assigned_agent_id: int | None = None) -> int:
    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO work_items (project_id,title,description,status,priority,assigned_agent_id) VALUES (?,?,?,?,?,?)",
            (project_id, title, description, status, priority, assigned_agent_id),
        )
        await db.commit()
        return cur.lastrowid


async def update_work_item(item_id: int, **kwargs) -> bool:
    allowed = {"title", "description", "status", "priority", "assigned_agent_id", "match_score", "match_reason"}
    fields, values = [], []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        return False
    fields.append("updated_at = datetime('now')")
    values.append(item_id)
    async with connect() as db:
        cur = await db.execute(
            f"UPDATE work_items SET {', '.join(fields)} WHERE id = ?", values
        )
        await db.commit()
        return cur.rowcount > 0


async def delete_work_item(item_id: int) -> bool:
    async with connect() as db:
        cur = await db.execute("DELETE FROM work_items WHERE id = ?", (item_id,))
        await db.commit()
        return cur.rowcount > 0


# ── Meetings ─────────────────────────────────────────────────────────────────

async def list_meetings() -> list[dict]:
    """Kèm `pending_approvals` = số cửa duyệt còn treo của cuộc họp đó.

    Không có con số này thì phải mở lần lượt từng phòng họp mới biết chỗ nào đang
    chờ mình duyệt. Đếm được ngay ở DB vì recover_interrupted_runs() lúc khởi động
    đã đánh 'failed' cho mọi lần chạy đứt giữa chừng — hàng còn 'running' là còn
    thật sự chờ (xem list_pending_approvals).
    """
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT m.*, ("
            "  SELECT COUNT(*) FROM workflow_outputs o"
            "  JOIN workflow_runs r ON r.id = o.run_id"
            "  WHERE r.meeting_id = m.id AND r.status = 'running'"
            "    AND o.review_status = 'waiting_review' AND o.agent_id IS NULL"
            ") AS pending_approvals "
            "FROM meetings m ORDER BY m.created_at DESC"
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def list_finalized_meetings(limit: int = 5) -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM meetings WHERE status='finalized' ORDER BY decided_at DESC LIMIT ?",
            (limit,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_meeting(meeting_id: int) -> dict | None:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM meetings WHERE id = ?", (meeting_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def create_meeting(title: str, topic: str = "", participants_json: str = "[]", project_id: int | None = None) -> int:
    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO meetings (title,topic,participants_json,project_id) VALUES (?,?,?,?)",
            (title, topic, participants_json, project_id),
        )
        await db.commit()
        return cur.lastrowid


async def finalize_meeting(meeting_id: int, decision_text: str) -> bool:
    """Chốt kế hoạch: lưu quyết định cuối cùng, cho phép Xanax ra lệnh dựa theo đó."""
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    async with connect() as db:
        cur = await db.execute(
            "UPDATE meetings SET status='finalized', decision_text=?, decided_at=?, ended_at=? WHERE id=?",
            (decision_text, now, now, meeting_id),
        )
        await db.commit()
        return cur.rowcount > 0


async def update_meeting(meeting_id: int, **kwargs) -> bool:
    allowed = {
        "title", "topic", "status", "participants_json", "ended_at", "project_id",
        "decision_text", "decided_at", "draft_minutes", "proposed_items_json",
    }
    fields, values = [], []
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        return False
    values.append(meeting_id)
    async with connect() as db:
        cur = await db.execute(
            f"UPDATE meetings SET {', '.join(fields)} WHERE id = ?", values
        )
        await db.commit()
        return cur.rowcount > 0


async def delete_meeting(meeting_id: int) -> bool:
    async with connect() as db:
        cur = await db.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))
        await db.commit()
        return cur.rowcount > 0


async def add_meeting_message(meeting_id: int, sender: str, sender_type: str, content: str) -> int:
    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO meeting_messages (meeting_id,sender,sender_type,content) VALUES (?,?,?,?)",
            (meeting_id, sender, sender_type, content),
        )
        await db.commit()
        return cur.lastrowid


async def get_meeting_messages(meeting_id: int) -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM meeting_messages WHERE meeting_id = ? ORDER BY created_at ASC",
            (meeting_id,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_recent_meeting_messages(limit: int = 8) -> list[dict]:
    """Return one row per recently active meeting, with its latest message."""
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """WITH ranked AS (
                 SELECT mm.meeting_id,
                        mm.sender AS last_sender,
                        mm.sender_type AS last_sender_type,
                        mm.content AS last_content,
                        mm.created_at AS last_created_at,
                        ROW_NUMBER() OVER (
                          PARTITION BY mm.meeting_id
                          ORDER BY mm.created_at DESC, mm.id DESC
                        ) AS rn,
                        COUNT(*) OVER (PARTITION BY mm.meeting_id) AS message_count
                 FROM meeting_messages AS mm
               )
               SELECT r.meeting_id, m.title AS meeting_name,
                      r.last_sender, r.last_sender_type, r.last_content,
                      r.last_created_at, r.message_count
               FROM ranked AS r
               JOIN meetings AS m ON m.id = r.meeting_id
               WHERE r.rn = 1
               ORDER BY r.last_created_at DESC, r.meeting_id DESC
               LIMIT ?""",
            (limit,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


# ── Benchmarks ───────────────────────────────────────────────────────────────

async def list_benchmarks() -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM benchmarks ORDER BY created_at DESC") as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_benchmark(benchmark_id: int) -> dict | None:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM benchmarks WHERE id = ?", (benchmark_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def create_benchmark(name: str, role_description: str = "",
                           test_cases_json: str = "[]", models_json: str = "[]") -> int:
    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO benchmarks (name,role_description,test_cases_json,models_json) VALUES (?,?,?,?)",
            (name, role_description, test_cases_json, models_json),
        )
        await db.commit()
        return cur.lastrowid


async def update_benchmark(benchmark_id: int, **kwargs) -> bool:
    content_fields = {
        "name", "role_description", "test_cases_json", "models_json",
    }
    allowed = content_fields | {"status", "completed_at"}
    fields, values = [], []
    for k, v in kwargs.items():
        if k in allowed and v is not None:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        return False
    values.append(benchmark_id)
    # Khoá điều kiện ngay trong UPDATE để một lượt chạy vừa chuyển sang running
    # không thể bị route sửa nội dung chen vào giữa bước kiểm tra và bước ghi.
    status_guard = (
        " AND status != 'running'"
        if any(key in content_fields and value is not None for key, value in kwargs.items())
        else ""
    )
    async with connect() as db:
        cur = await db.execute(
            f"UPDATE benchmarks SET {', '.join(fields)} WHERE id = ?{status_guard}",
            values,
        )
        await db.commit()
        return cur.rowcount > 0


async def delete_benchmark(benchmark_id: int) -> bool:
    async with connect() as db:
        cur = await db.execute("DELETE FROM benchmarks WHERE id = ?", (benchmark_id,))
        await db.commit()
        return cur.rowcount > 0


async def add_benchmark_result(benchmark_id: int, model: str, scores_json: str,
                                responses_json: str, recommendation: str) -> int:
    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO benchmark_results (benchmark_id,model,scores_json,responses_json,recommendation) VALUES (?,?,?,?,?)",
            (benchmark_id, model, scores_json, responses_json, recommendation),
        )
        await db.commit()
        return cur.lastrowid


async def get_benchmark_result(result_id: int) -> dict | None:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM benchmark_results WHERE id=?", (result_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def get_benchmark_results(benchmark_id: int) -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM benchmark_results WHERE benchmark_id = ? ORDER BY created_at ASC",
            (benchmark_id,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


# ── Thí nghiệm cơ chế tự cải thiện ──────────────────────────────────────────

async def create_experiment(
    name: str,
    agent_id: int,
    project_id: int | None,
    benchmark_id: int,
    measured_model_pool_id: int,
    judge_model_pool_id: int,
    repetitions: int = 3,
    warnings_json: str = "[]",
) -> int:
    async with connect() as db:
        cur = await db.execute(
            """INSERT INTO experiments
               (name,agent_id,project_id,benchmark_id,measured_model_pool_id,
                judge_model_pool_id,repetitions,warnings_json)
               VALUES (?,?,?,?,?,?,?,?)""",
            (name, agent_id, project_id, benchmark_id, measured_model_pool_id,
             judge_model_pool_id, repetitions, warnings_json),
        )
        await db.commit()
        return cur.lastrowid


async def list_experiments() -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT e.*, a.name AS agent_name, p.name AS project_name,
                      b.name AS benchmark_name, measured.name AS measured_model_name,
                      judge.name AS judge_model_name
               FROM experiments e
               LEFT JOIN agent_configs a ON a.id=e.agent_id
               LEFT JOIN projects p ON p.id=e.project_id
               LEFT JOIN benchmarks b ON b.id=e.benchmark_id
               LEFT JOIN model_pool measured ON measured.id=e.measured_model_pool_id
               LEFT JOIN model_pool judge ON judge.id=e.judge_model_pool_id
               ORDER BY e.created_at DESC, e.id DESC"""
        ) as cur:
            return [dict(row) for row in await cur.fetchall()]


async def get_experiment(experiment_id: int) -> dict | None:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT e.*, a.name AS agent_name, p.name AS project_name,
                      b.name AS benchmark_name, measured.name AS measured_model_name,
                      measured.model_id AS measured_model_id,
                      judge.name AS judge_model_name, judge.model_id AS judge_model_id
               FROM experiments e
               LEFT JOIN agent_configs a ON a.id=e.agent_id
               LEFT JOIN projects p ON p.id=e.project_id
               LEFT JOIN benchmarks b ON b.id=e.benchmark_id
               LEFT JOIN model_pool measured ON measured.id=e.measured_model_pool_id
               LEFT JOIN model_pool judge ON judge.id=e.judge_model_pool_id
               WHERE e.id=?""",
            (experiment_id,),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def update_experiment(experiment_id: int, **kwargs) -> bool:
    allowed = {
        "status", "total_trials", "completed_trials", "scored_trials",
        "warnings_json", "config_snapshot_json", "soul_snapshot_json",
        "error_text", "started_at", "completed_at",
    }
    fields: list[str] = []
    values: list = []
    for key, value in kwargs.items():
        if key in allowed:
            fields.append(f"{key}=?")
            values.append(value)
    if not fields:
        return False
    fields.append("updated_at=datetime('now')")
    values.append(experiment_id)
    async with connect() as db:
        cur = await db.execute(
            f"UPDATE experiments SET {','.join(fields)} WHERE id=?", values
        )
        await db.commit()
        return cur.rowcount > 0


async def claim_experiment_run(
    experiment_id: int,
    *,
    total_trials: int,
    config_snapshot_json: str,
    soul_snapshot_json: str,
    warnings_json: str,
) -> bool:
    """Chuyển pending→running nguyên tử để hai client không chạy trùng."""
    async with connect() as db:
        cur = await db.execute(
            """UPDATE experiments SET status='running', total_trials=?,
                      completed_trials=0, scored_trials=0,
                      config_snapshot_json=?, soul_snapshot_json=?, warnings_json=?,
                      error_text='', started_at=datetime('now'), completed_at=NULL,
                      updated_at=datetime('now')
               WHERE id=? AND status='pending'""",
            (total_trials, config_snapshot_json, soul_snapshot_json,
             warnings_json, experiment_id),
        )
        await db.commit()
        return cur.rowcount == 1


async def create_experiment_trials(experiment_id: int, trials: list[dict]) -> None:
    """Tạo toàn bộ ô đo trước khi gọi model để huỷ giữa chừng vẫn thấy phần thiếu."""
    values = [(
        experiment_id, item["condition"], item["case_index"], item["repetition"],
        item["execution_order"], item["prompt"], item.get("criteria", ""),
    ) for item in trials]
    async with connect() as db:
        await db.executemany(
            """INSERT INTO experiment_trials
               (experiment_id,condition,case_index,repetition,execution_order,prompt,criteria)
               VALUES (?,?,?,?,?,?,?)""",
            values,
        )
        await db.commit()


async def list_experiment_trials(experiment_id: int) -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM experiment_trials WHERE experiment_id=? ORDER BY execution_order,id",
            (experiment_id,),
        ) as cur:
            return [dict(row) for row in await cur.fetchall()]


async def get_experiment_trial(trial_id: int) -> dict | None:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM experiment_trials WHERE id=?", (trial_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def update_experiment_trial(trial_id: int, **kwargs) -> bool:
    allowed = {
        "judge_order", "response", "score", "score_reason", "response_classification", "status",
        "error_text", "elapsed_seconds", "tokens_input", "tokens_cache",
        "tokens_output", "judgement_id", "started_at", "completed_at",
    }
    fields: list[str] = []
    values: list = []
    for key, value in kwargs.items():
        if key in allowed:
            fields.append(f"{key}=?")
            values.append(value)
    if not fields:
        return False
    values.append(trial_id)
    async with connect() as db:
        cur = await db.execute(
            f"UPDATE experiment_trials SET {','.join(fields)} WHERE id=?", values
        )
        await db.commit()
        return cur.rowcount > 0


async def create_experiment_judgement(
    experiment_id: int,
    case_index: int,
    judge_model_pool_id: int,
    item_map_json: str,
    judge_prompt: str,
) -> int:
    async with connect() as db:
        cur = await db.execute(
            """INSERT INTO experiment_judgements
               (experiment_id,case_index,judge_model_pool_id,item_map_json,judge_prompt,status)
               VALUES (?,?,?,?,?,'running')""",
            (experiment_id, case_index, judge_model_pool_id, item_map_json, judge_prompt),
        )
        await db.commit()
        return cur.lastrowid


async def update_experiment_judgement(judgement_id: int, **kwargs) -> bool:
    allowed = {
        "raw_response", "status", "error_text", "elapsed_seconds",
        "tokens_input", "tokens_cache", "tokens_output", "completed_at",
    }
    fields: list[str] = []
    values: list = []
    for key, value in kwargs.items():
        if key in allowed:
            fields.append(f"{key}=?")
            values.append(value)
    if not fields:
        return False
    values.append(judgement_id)
    async with connect() as db:
        cur = await db.execute(
            f"UPDATE experiment_judgements SET {','.join(fields)} WHERE id=?", values
        )
        await db.commit()
        return cur.rowcount > 0


async def list_experiment_judgements(experiment_id: int) -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM experiment_judgements WHERE experiment_id=? ORDER BY case_index,id",
            (experiment_id,),
        ) as cur:
            return [dict(row) for row in await cur.fetchall()]


async def refresh_experiment_progress(experiment_id: int) -> dict:
    async with connect() as db:
        async with db.execute(
            """SELECT COUNT(*),
                      COALESCE(SUM(CASE WHEN status NOT IN ('pending','running','cancelled') THEN 1 ELSE 0 END),0),
                      COALESCE(SUM(CASE WHEN score IS NOT NULL THEN 1 ELSE 0 END),0)
               FROM experiment_trials WHERE experiment_id=?""",
            (experiment_id,),
        ) as cur:
            total, completed, scored = await cur.fetchone()
        await db.execute(
            """UPDATE experiments SET total_trials=?,completed_trials=?,scored_trials=?,
                      updated_at=datetime('now') WHERE id=?""",
            (total, completed, scored, experiment_id),
        )
        await db.commit()
    return {"total_trials": total, "completed_trials": completed, "scored_trials": scored}


async def cancel_unfinished_experiment_trials(experiment_id: int) -> None:
    async with connect() as db:
        await db.execute(
            """UPDATE experiment_trials SET status='cancelled',completed_at=datetime('now')
               WHERE experiment_id=? AND status IN ('pending','running','generated','judging')""",
            (experiment_id,),
        )
        await db.execute(
            """UPDATE experiment_judgements
               SET status='cancelled',completed_at=datetime('now')
               WHERE experiment_id=? AND status='running'""",
            (experiment_id,),
        )
        await db.commit()


async def recover_interrupted_experiments() -> int:
    """Đánh dấu lượt đang chạy khi server cũ đã chết; không xoá dữ liệu dở dang."""
    async with connect() as db:
        await db.execute(
            """UPDATE experiment_trials SET status='interrupted',completed_at=datetime('now')
               WHERE status IN ('running','judging')"""
        )
        cur = await db.execute(
            """UPDATE experiments SET status='interrupted',completed_at=datetime('now'),
                      error_text='Server dừng khi thí nghiệm đang chạy',updated_at=datetime('now')
               WHERE status='running'"""
        )
        await db.commit()
        return cur.rowcount


# ── Task Alerts ───────────────────────────────────────────────────────────────

async def create_task_alert(
    work_item_id: int, project_id: int, title: str,
    reason: str = "no_matching_agent", suggestions_json: str = "[]"
) -> int:
    """Create or replace an open alert for a work item."""
    async with connect() as db:
        # Remove any existing open alert for this item
        await db.execute(
            "DELETE FROM task_alerts WHERE work_item_id = ? AND status = 'open'",
            (work_item_id,)
        )
        cur = await db.execute(
            "INSERT INTO task_alerts (work_item_id, project_id, title, reason, suggestions_json) VALUES (?,?,?,?,?)",
            (work_item_id, project_id, title, reason, suggestions_json),
        )
        await db.commit()
        return cur.lastrowid


async def list_task_alerts(status: str = "open") -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT ta.*, p.name as project_name "
            "FROM task_alerts ta JOIN projects p ON p.id = ta.project_id "
            "WHERE ta.status = ? ORDER BY ta.created_at DESC",
            (status,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def resolve_task_alert(work_item_id: int) -> bool:
    async with connect() as db:
        cur = await db.execute(
            "UPDATE task_alerts SET status='resolved', resolved_at=datetime('now') "
            "WHERE work_item_id = ? AND status = 'open'",
            (work_item_id,),
        )
        await db.commit()
        return cur.rowcount > 0


async def delete_task_alert_for_item(work_item_id: int) -> None:
    async with connect() as db:
        await db.execute("DELETE FROM task_alerts WHERE work_item_id = ?", (work_item_id,))
        await db.commit()


async def get_open_alert_count() -> int:
    async with connect() as db:
        async with db.execute(
            "SELECT COUNT(*) FROM task_alerts WHERE status = 'open'"
        ) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0


# ── Workflow Tasks ────────────────────────────────────────────────────────────

async def create_workflow_task(
    name: str, description: str = "", project_id: int | None = None,
    agents_json: str = "[]", schedule_enabled: int = 0, schedule_cron: str = "",
    graph_json: str = "", trigger_type: str = "manual", trigger_config_json: str = "{}",
    kind: str = "automation",
) -> int:
    from core.slugify import slugify

    async with connect() as db:
        slug = await _unique_slug(db, "workflow_tasks", slugify(name, fallback="quy-trinh"))
        cur = await db.execute(
            """INSERT INTO workflow_tasks
               (name,description,project_id,agents_json,schedule_enabled,schedule_cron,
                graph_json,trigger_type,trigger_config_json,slug,kind)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (name, description, project_id, agents_json, schedule_enabled, schedule_cron,
             graph_json, trigger_type, trigger_config_json, slug, kind),
        )
        await db.commit()
        return cur.lastrowid


async def list_workflow_tasks_by_trigger(trigger_type: str) -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM workflow_tasks WHERE status='active'",
        ) as cur:
            tasks = [dict(r) for r in await cur.fetchall()]
    matched = []
    for task in tasks:
        if task.get("trigger_type") == trigger_type:
            matched.append(task)
            continue
        try:
            config = json.loads(task.get("trigger_config_json") or "{}")
            enabled = bool(config.get("triggers", {}).get(trigger_type, {}).get("enabled"))
        except (TypeError, ValueError, AttributeError):
            enabled = False
        if enabled:
            matched.append(task)
    return matched


async def list_workflow_tasks(project_id: int | None = None, kind: str | None = None) -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        clauses = ["status!='archived'"]
        params_list: list = []
        if project_id is not None:
            clauses.append("project_id=?")
            params_list.append(project_id)
        if kind is not None:
            clauses.append("kind=?")
            params_list.append(kind)
        sql = f"SELECT * FROM workflow_tasks WHERE {' AND '.join(clauses)} ORDER BY created_at DESC"
        params = tuple(params_list)
        async with db.execute(sql, params) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_workflow_task(task_id: int) -> dict | None:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM workflow_tasks WHERE id=?", (task_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def update_workflow_task(task_id: int, **kwargs) -> bool:
    allowed = {"name", "description", "project_id", "agents_json", "schedule_enabled", "schedule_cron", "status", "kind",
               "graph_json", "trigger_type", "trigger_config_json"}
    fields, values = [], []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        return False
    fields.append("updated_at = datetime('now')")
    values.append(task_id)
    async with connect() as db:
        cur = await db.execute(f"UPDATE workflow_tasks SET {', '.join(fields)} WHERE id=?", values)
        await db.commit()
        return cur.rowcount > 0


async def delete_workflow_task(task_id: int) -> bool:
    async with connect() as db:
        cur = await db.execute("DELETE FROM workflow_tasks WHERE id=?", (task_id,))
        await db.commit()
        return cur.rowcount > 0


# ── Workflow Runs ─────────────────────────────────────────────────────────────

async def create_workflow_run(
    task_id: int, project_id: int | None = None,
    task_name: str = "", triggered_by: str = "manual",
    meeting_id: int | None = None,
) -> int:
    """meeting_id = cuộc họp đã kích hoạt lần chạy này.

    Cần lưu xuống DB chứ không giữ trong RAM: yêu cầu duyệt trước đây chỉ được đẩy
    một lần qua WebSocket, nên đóng phòng họp rồi mở lại là mất thẻ duyệt. Có cột
    này mới tìm ngược được "cuộc họp đang có bao nhiêu việc chờ tôi duyệt".
    """
    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO workflow_runs (task_id,project_id,task_name,triggered_by,meeting_id) "
            "VALUES (?,?,?,?,?)",
            (task_id, project_id, task_name, triggered_by, meeting_id),
        )
        await db.commit()
        return cur.lastrowid


async def list_pending_approvals(meeting_id: int | None = None) -> list[dict]:
    """Các cửa duyệt (node approval_gate) đang đứng chờ người duyệt.

    Nhận diện bằng agent_id IS NULL: mọi bước do nhân viên chạy đều có agent_id,
    riêng output của cửa duyệt thì không. Lọc theo tên "Chờ ... duyệt" là hỏng ngay
    khi ai đó đổi tên người duyệt trong cấu hình node.

    Chỉ lấy lần chạy còn 'running' — lần chạy đã xong/thất bại thì cửa duyệt của nó
    không còn ý nghĩa gì.
    """
    sql = (
        "SELECT o.id AS output_id, o.run_id, o.agent_name, o.output_content, "
        "       o.created_at, r.task_name, r.meeting_id, r.project_id "
        "FROM workflow_outputs o JOIN workflow_runs r ON r.id = o.run_id "
        "WHERE o.review_status = 'waiting_review' AND o.agent_id IS NULL "
        "  AND r.status = 'running'"
    )
    params: tuple = ()
    if meeting_id is not None:
        sql += " AND r.meeting_id = ?"
        params = (meeting_id,)
    sql += " ORDER BY o.id ASC"
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        rows = await (await db.execute(sql, params)).fetchall()
        return [dict(r) for r in rows]


async def list_workflow_runs(
    task_id: int | None = None, project_id: int | None = None, limit: int = 50
) -> list[dict]:
    conditions, params = [], []
    if task_id is not None:
        conditions.append("task_id = ?")
        params.append(task_id)
    if project_id is not None:
        conditions.append("project_id = ?")
        params.append(project_id)
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    params.append(limit)
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            f"SELECT * FROM workflow_runs {where} ORDER BY created_at DESC LIMIT ?", params
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def list_workflow_runs_by_status(status: str) -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM workflow_runs WHERE status = ? ORDER BY created_at DESC", (status,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_workflow_run(run_id: int) -> dict | None:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM workflow_runs WHERE id=?", (run_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def update_workflow_run_status(
    run_id: int, status: str, *, set_started: bool = False, set_completed: bool = False
) -> None:
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    fields = ["status = ?"]
    values: list = [status]
    if set_started:
        fields.append("started_at = ?")
        values.append(now)
    if set_completed:
        fields.append("completed_at = ?")
        values.append(now)
    values.append(run_id)
    async with connect() as db:
        await db.execute(f"UPDATE workflow_runs SET {', '.join(fields)} WHERE id=?", values)
        await db.commit()


async def delete_workflow_run(run_id: int) -> bool:
    async with connect() as db:
        cur = await db.execute("DELETE FROM workflow_runs WHERE id=?", (run_id,))
        await db.commit()
        return cur.rowcount > 0


async def update_workflow_run_review(run_id: int, **kwargs) -> None:
    allowed = {
        "review_status", "priority", "output_type", "feedback", "ready_for_next",
        "reviewed_at", "archive_payload_json", "last_action_test",
    }
    fields, values = [], []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        return
    values.append(run_id)
    async with connect() as db:
        await db.execute(f"UPDATE workflow_runs SET {', '.join(fields)} WHERE id=?", values)
        await db.commit()


# ── Workflow Outputs ──────────────────────────────────────────────────────────

async def create_workflow_output(
    run_id: int, task_id: int, agent_id: int | None, agent_name: str, step_order: int
) -> int:
    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO workflow_outputs (run_id,task_id,agent_id,agent_name,step_order) VALUES (?,?,?,?,?)",
            (run_id, task_id, agent_id, agent_name, step_order),
        )
        await db.commit()
        return cur.lastrowid


async def list_workflow_outputs(run_id: int) -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM workflow_outputs WHERE run_id=? ORDER BY step_order ASC", (run_id,)
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def list_agent_run_history(agent_id: int, limit: int = 15) -> list[dict]:
    """Lịch sử các lần nhân viên này đã chạy trong quy trình (workflow_outputs), mới nhất
    trước — dùng để trưởng phòng (và chính nhân viên qua soul.md) biết được công việc đã
    làm trước đây, không chỉ work_items đang active. Xem api/websocket_meeting.py
    _department_head_context — trước đây chỉ có Xanax mới truy xuất được dữ liệu này."""
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT wo.*, wr.task_name, wr.completed_at
               FROM workflow_outputs wo
               LEFT JOIN workflow_runs wr ON wr.id = wo.run_id
               WHERE wo.agent_id = ?
               ORDER BY wo.created_at DESC LIMIT ?""",
            (agent_id, limit),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_workflow_output(output_id: int) -> dict | None:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT wo.*, wr.task_name
               FROM workflow_outputs wo
               LEFT JOIN workflow_runs wr ON wr.id = wo.run_id
               WHERE wo.id=?""",
            (output_id,)
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def update_workflow_output(output_id: int, **kwargs) -> None:
    allowed = {
        "output_content", "status", "pass_fail", "edited_content", "notes", "tokens_input", "tokens_output",
        "review_status", "priority", "output_type", "feedback", "ready_for_next", "reviewed_at", "archive_payload_json",
        "finished_at", "last_action_test",
    }
    fields, values = [], []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        return
    values.append(output_id)
    async with connect() as db:
        await db.execute(f"UPDATE workflow_outputs SET {', '.join(fields)} WHERE id=?", values)
        await db.commit()


# ── Project Ops Dashboard (Overview / Runs / Review Queue / Kanban / History) ──
# Mỗi item trong ops = 1 workflow_run. Chi tiết từng bước vẫn lấy từ
# workflow_outputs khi người dùng mở popup chi tiết.

_OPS_RUN_SELECT = """
    SELECT
        wr.id AS run_id, wr.task_id, wr.project_id, wr.task_name AS workflow_name,
        wr.status AS run_status, wr.triggered_by, wr.started_at, wr.completed_at, wr.created_at,
        wr.review_status, wr.priority, wr.output_type, wr.feedback, wr.ready_for_next,
        wr.reviewed_at, wr.archive_payload_json, wr.last_action_test,
        wo.id AS output_id, wo.agent_id, wo.agent_name AS output_agent_name, wo.step_order,
        wo.output_content, wo.edited_content, wo.finished_at AS output_finished_at, wo.created_at AS output_created_at,
        COALESCE(ac.name, wo.agent_name) AS agent_name,
        ac.role AS agent_role, ac.avatar_color AS agent_color
    FROM workflow_runs wr
    LEFT JOIN workflow_outputs wo ON wo.run_id = wr.id
    LEFT JOIN agent_configs ac ON ac.id = wo.agent_id
"""


def _shape_ops_run_rows(rows: list[dict]) -> list[dict]:
    grouped: dict[int, dict] = {}
    for row in rows:
        run_id = row["run_id"]
        run = grouped.get(run_id)
        if not run:
            run = {
                "id": run_id,
                "task_id": row["task_id"],
                "project_id": row["project_id"],
                "workflow_name": row.get("workflow_name") or "Quy trình",
                "run_status": row.get("run_status") or "pending",
                "triggered_by": row.get("triggered_by") or "manual",
                "started_at": row.get("started_at") or row.get("created_at"),
                "completed_at": row.get("completed_at"),
                "created_at": row.get("created_at"),
                "review_status": row.get("review_status") or "waiting_review",
                "priority": row.get("priority") or "medium",
                "output_type": row.get("output_type") or "text",
                "feedback": row.get("feedback"),
                "ready_for_next": row.get("ready_for_next", 0),
                "reviewed_at": row.get("reviewed_at"),
                "archive_payload_json": row.get("archive_payload_json"),
                "last_action_test": row.get("last_action_test", 0),
                "outputs": [],
            }
            grouped[run_id] = run
        if row.get("output_id") is not None:
            run["outputs"].append({
                "id": row["output_id"],
                "agent_id": row.get("agent_id"),
                "agent_name": row.get("agent_name") or row.get("output_agent_name") or "Nhân viên AI",
                "agent_role": row.get("agent_role") or "",
                "agent_color": row.get("agent_color"),
                "step_order": row.get("step_order") or 0,
                "output_content": row.get("output_content") or "",
                "edited_content": row.get("edited_content") or "",
                "finished_at": row.get("output_finished_at"),
                "created_at": row.get("output_created_at"),
            })

    result = []
    for run in grouped.values():
        outputs = sorted(run["outputs"], key=lambda o: (o.get("step_order", 0), o.get("created_at") or ""))
        agents, seen = [], set()
        for output in outputs:
            key = (output.get("agent_id"), output.get("agent_name"))
            if key in seen:
                continue
            seen.add(key)
            agents.append({
                "agentId": output.get("agent_id"),
                "agentName": output.get("agent_name") or "Nhân viên AI",
                "agentRole": output.get("agent_role") or "",
                "agentColor": output.get("agent_color"),
            })
        content_parts = []
        for output in outputs:
            content = output.get("edited_content") or output.get("output_content") or ""
            if content.strip():
                content_parts.append(content.strip())
        preview = "\n\n".join(content_parts).strip()
        summary = preview[:150] + "…" if len(preview) > 150 else preview
        run["agents"] = agents
        run["agent_count"] = len(agents)
        run["output_count"] = len(outputs)
        run["summary"] = summary or "(chưa có nội dung)"
        run["output_preview"] = preview or "(chưa có nội dung)"
        result.append(run)
    return sorted(result, key=lambda r: (r.get("started_at") or r.get("created_at") or "", r["id"]), reverse=True)


async def list_ops_items(project_id: int) -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            _OPS_RUN_SELECT + " WHERE wr.project_id=? ORDER BY COALESCE(wr.started_at, wr.created_at) DESC, wo.step_order ASC, wo.created_at ASC",
            (project_id,),
        ) as cur:
            return _shape_ops_run_rows([dict(r) for r in await cur.fetchall()])


async def get_ops_item(run_id: int) -> dict | None:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            _OPS_RUN_SELECT + " WHERE wr.id=? ORDER BY wo.step_order ASC, wo.created_at ASC",
            (run_id,),
        ) as cur:
            rows = [dict(r) for r in await cur.fetchall()]
            if not rows:
                return None
            shaped = _shape_ops_run_rows(rows)
            return shaped[0] if shaped else None


async def create_ops_history(
    project_id: int,
    output_id: int | None,
    type_: str,
    text: str,
    *,
    run_id: int | None = None,
) -> int:
    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO ops_history (project_id,output_id,run_id,type,text) VALUES (?,?,?,?,?)",
            (project_id, output_id, run_id, type_, text),
        )
        await db.commit()
        return cur.lastrowid


async def list_ops_history(project_id: int, limit: int = 200) -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM ops_history WHERE project_id=? ORDER BY created_at DESC LIMIT ?",
            (project_id, limit),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


# ── Model Pool ────────────────────────────────────────────────────────────────

async def create_model_pool_entry(
    name: str,
    provider: str,
    api_style: str = "openai_compat",
    model_id: str = "",
    base_url: str = "",
    api_key: str = "",
    category: str = "general",
    max_requests_per_day: int = 0,
    max_tokens_per_day: int = 0,
    price_input_per_1m: float = 0,
    price_cache_per_1m: float = 0,
    price_output_per_1m: float = 0,
    currency: str = "USD",
    cli_config_dir: str = "",
) -> int:
    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO model_pool (name,provider,api_style,model_id,base_url,api_key,category,"
            "max_requests_per_day,max_tokens_per_day,price_input_per_1m,price_cache_per_1m,price_output_per_1m,currency,"
            "cli_config_dir) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (name, provider, api_style, model_id, base_url, api_key, category,
             max_requests_per_day, max_tokens_per_day,
             price_input_per_1m, price_cache_per_1m, price_output_per_1m, currency,
             cli_config_dir),
        )
        await db.commit()
        return cur.lastrowid


async def list_model_pool(enabled_only: bool = False) -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        q = "SELECT * FROM model_pool"
        if enabled_only:
            q += " WHERE enabled=1"
        q += " ORDER BY created_at ASC"
        async with db.execute(q) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_model_pool_entry(entry_id: int) -> dict | None:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM model_pool WHERE id=?", (entry_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def update_model_pool_entry(entry_id: int, **kwargs) -> bool:
    allowed = {"name", "provider", "api_style", "model_id", "base_url", "api_key", "category",
               "max_requests_per_day", "max_tokens_per_day", "enabled",
               "price_input_per_1m", "price_cache_per_1m", "price_output_per_1m", "currency",
               "cli_config_dir"}
    fields, values = [], []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k}=?")
            values.append(v)
    if not fields:
        return False
    values.append(entry_id)
    async with connect() as db:
        cur = await db.execute(
            f"UPDATE model_pool SET {','.join(fields)} WHERE id=?", values
        )
        await db.commit()
        return cur.rowcount > 0


async def delete_model_pool_entry(entry_id: int) -> bool:
    async with connect() as db:
        cur = await db.execute("DELETE FROM model_pool WHERE id=?", (entry_id,))
        await db.commit()
        return cur.rowcount > 0


async def record_model_usage(
    model_pool_id: int,
    tokens_input: int = 0,
    tokens_output: int = 0,
    tokens_cache: int = 0,
) -> None:
    today = _local_now().strftime("%Y-%m-%d")
    async with connect() as db:
        await db.execute(
            """INSERT INTO model_usage (model_pool_id, date, request_count, tokens_input, tokens_cache, tokens_output)
               VALUES (?,?,1,?,?,?)
               ON CONFLICT(model_pool_id, date) DO UPDATE SET
                 request_count = request_count + 1,
                 tokens_input  = tokens_input  + excluded.tokens_input,
                 tokens_cache  = tokens_cache  + excluded.tokens_cache,
                 tokens_output = tokens_output + excluded.tokens_output""",
            (model_pool_id, today, tokens_input, tokens_cache, tokens_output),
        )
        await db.commit()


async def record_model_usage_hourly(
    model_pool_id: int,
    tokens_input: int = 0,
    tokens_output: int = 0,
    tokens_cache: int = 0,
) -> None:
    now = _local_now()
    today = now.strftime("%Y-%m-%d")
    hour = now.hour
    async with connect() as db:
        await db.execute(
            """INSERT INTO model_usage_hourly (model_pool_id, date, hour, request_count, tokens_input, tokens_cache, tokens_output)
               VALUES (?,?,?,1,?,?,?)
               ON CONFLICT(model_pool_id, date, hour) DO UPDATE SET
                 request_count = request_count + 1,
                 tokens_input  = tokens_input  + excluded.tokens_input,
                 tokens_cache  = tokens_cache  + excluded.tokens_cache,
                 tokens_output = tokens_output + excluded.tokens_output""",
            (model_pool_id, today, hour, tokens_input, tokens_cache, tokens_output),
        )
        await db.commit()


async def get_model_usage_hourly_range(date: str) -> list[dict]:
    """Trả về từng dòng (model_pool_id, hour, request_count, tokens_input,
    tokens_cache, tokens_output) trong 1 ngày (YYYY-MM-DD), kèm thông tin model
    để tầng API tính tiền theo giờ (0-23h)."""
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT mu.model_pool_id, mu.hour, mu.request_count,
                      mu.tokens_input, mu.tokens_cache, mu.tokens_output,
                      mp.name, mp.model_id AS model_id_str, mp.provider, mp.category,
                      mp.price_input_per_1m, mp.price_cache_per_1m, mp.price_output_per_1m,
                      mp.currency
               FROM model_usage_hourly mu
               JOIN model_pool mp ON mp.id = mu.model_pool_id
               WHERE mu.date = ?
               ORDER BY mu.hour ASC""",
            (date,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def record_model_call_log(
    model_pool_id: int,
    tokens_input: int = 0,
    tokens_output: int = 0,
    tokens_cache: int = 0,
) -> None:
    """Ghi lại 1 dòng cho MỖI lượt gọi model (khác với model_usage/model_usage_hourly
    là tổng theo ngày/giờ) — dùng để tra cứu chi tiết từng lượt chạy kèm thời gian
    chính xác trong tab Chi phí."""
    called_at = _local_now().strftime("%Y-%m-%d %H:%M:%S")
    async with connect() as db:
        await db.execute(
            """INSERT INTO model_call_log (model_pool_id, called_at, tokens_input, tokens_cache, tokens_output)
               VALUES (?,?,?,?,?)""",
            (model_pool_id, called_at, tokens_input, tokens_cache, tokens_output),
        )
        await db.commit()


async def get_model_call_log_for_date(date: str) -> list[dict]:
    """Trả về từng lượt gọi (called_at, tokens_input, tokens_cache, tokens_output)
    trong 1 ngày (YYYY-MM-DD), kèm thông tin model để tính tiền từng lượt."""
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT mcl.model_pool_id, mcl.called_at,
                      mcl.tokens_input, mcl.tokens_cache, mcl.tokens_output,
                      mp.name, mp.model_id AS model_id_str, mp.provider, mp.category,
                      mp.price_input_per_1m, mp.price_cache_per_1m, mp.price_output_per_1m,
                      mp.currency
               FROM model_call_log mcl
               JOIN model_pool mp ON mp.id = mcl.model_pool_id
               WHERE mcl.called_at LIKE ?
               ORDER BY mcl.called_at DESC""",
            (f"{date}%",),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_model_usage_today(model_pool_id: int) -> dict:
    today = _local_now().strftime("%Y-%m-%d")
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM model_usage WHERE model_pool_id=? AND date=?",
            (model_pool_id, today),
        ) as cur:
            row = await cur.fetchone()
            return dict(row) if row else {"request_count": 0, "tokens_input": 0, "tokens_cache": 0, "tokens_output": 0}


async def get_top_models_usage(limit: int = 10) -> list[dict]:
    """Returns top models by total request_count across all dates."""
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT mp.id, mp.name, mp.model_id, mp.category, mp.provider,
                      COALESCE(SUM(mu.request_count),0) AS total_requests,
                      COALESCE(SUM(mu.tokens_input+mu.tokens_output),0) AS total_tokens
               FROM model_pool mp
               LEFT JOIN model_usage mu ON mu.model_pool_id = mp.id
               GROUP BY mp.id
               ORDER BY total_requests DESC
               LIMIT ?""",
            (limit,),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_model_usage_range(date_from: str, date_to: str) -> list[dict]:
    """Trả về từng dòng (model_pool_id, date, request_count, tokens_input,
    tokens_cache, tokens_output) trong khoảng [date_from, date_to] (YYYY-MM-DD,
    inclusive cả hai đầu), kèm thông tin model (name, provider, price, currency)
    để tầng API tự nhóm theo ngày/tuần/tháng và tính tiền — nhóm theo period ở
    Python cho đơn giản, không cần SQL strftime phức tạp cho tuần ISO."""
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """SELECT mu.model_pool_id, mu.date, mu.request_count,
                      mu.tokens_input, mu.tokens_cache, mu.tokens_output,
                      mp.name, mp.model_id AS model_id_str, mp.provider, mp.category,
                      mp.price_input_per_1m, mp.price_cache_per_1m, mp.price_output_per_1m,
                      mp.currency
               FROM model_usage mu
               JOIN model_pool mp ON mp.id = mu.model_pool_id
               WHERE mu.date >= ? AND mu.date <= ?
               ORDER BY mu.date ASC""",
            (date_from, date_to),
        ) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def create_xanax_note(content: str) -> int:
    async with connect() as db:
        cur = await db.execute("INSERT INTO xanax_notes (content) VALUES (?)", (content,))
        await db.commit()
        return cur.lastrowid


async def list_xanax_notes() -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM xanax_notes ORDER BY created_at DESC") as cur:
            return [dict(r) for r in await cur.fetchall()]


async def delete_xanax_note(note_id: int) -> bool:
    async with connect() as db:
        cur = await db.execute("DELETE FROM xanax_notes WHERE id = ?", (note_id,))
        await db.commit()
        return cur.rowcount > 0


# ── Assets (file upload thủ công, lưu trên đĩa — DB chỉ giữ metadata) ────────

async def create_asset(filename: str, stored_path: str, mime_type: str = "",
                        size_bytes: int = 0, source: str = "upload", note: str = "") -> int:
    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO assets (filename,stored_path,mime_type,size_bytes,source,note) VALUES (?,?,?,?,?,?)",
            (filename, stored_path, mime_type, size_bytes, source, note),
        )
        await db.commit()
        return cur.lastrowid


async def list_assets() -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM assets ORDER BY created_at DESC") as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_asset(asset_id: int) -> dict | None:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM assets WHERE id=?", (asset_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def delete_asset(asset_id: int) -> bool:
    async with connect() as db:
        cur = await db.execute("DELETE FROM assets WHERE id=?", (asset_id,))
        await db.commit()
        return cur.rowcount > 0


# ── Knowledge Documents (RAG "phòng tư liệu") ────────────────────────────────

async def create_knowledge_document(title: str, content: str, project_id: int | None = None, tags: str = "") -> int:
    async with connect() as db:
        cur = await db.execute(
            "INSERT INTO knowledge_documents (project_id,title,content,tags) VALUES (?,?,?,?)",
            (project_id, title, content, tags),
        )
        await db.commit()
        return cur.lastrowid


async def list_knowledge_documents(project_id: int | None = None) -> list[dict]:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        if project_id is not None:
            sql = "SELECT * FROM knowledge_documents WHERE project_id=? OR project_id IS NULL ORDER BY created_at DESC"
            params: tuple = (project_id,)
        else:
            sql = "SELECT * FROM knowledge_documents ORDER BY created_at DESC"
            params = ()
        async with db.execute(sql, params) as cur:
            return [dict(r) for r in await cur.fetchall()]


async def get_knowledge_document(doc_id: int) -> dict | None:
    async with connect() as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM knowledge_documents WHERE id=?", (doc_id,)) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None


async def update_knowledge_document(doc_id: int, **kwargs) -> bool:
    allowed = {"title", "content", "tags", "project_id"}
    fields, values = [], []
    for k, v in kwargs.items():
        if k in allowed:
            fields.append(f"{k} = ?")
            values.append(v)
    if not fields:
        return False
    fields.append("updated_at = datetime('now')")
    values.append(doc_id)
    async with connect() as db:
        cur = await db.execute(f"UPDATE knowledge_documents SET {', '.join(fields)} WHERE id=?", values)
        await db.commit()
        return cur.rowcount > 0


async def delete_knowledge_document(doc_id: int) -> bool:
    async with connect() as db:
        cur = await db.execute("DELETE FROM knowledge_documents WHERE id=?", (doc_id,))
        await db.commit()
        return cur.rowcount > 0


async def get_all_agents_with_skills() -> list[dict]:
    """Return all enabled agents with their skills list deserialized."""
    import json
    agents = await list_agent_configs()
    enabled = [a for a in agents if a.get("enabled", 1)]
    all_skills = await list_skills()
    skill_map = {s["id"]: s for s in all_skills}
    for agent in enabled:
        try:
            skill_ids = json.loads(agent.get("skills_json", "[]"))
        except Exception:
            skill_ids = []
        agent["skills"] = [skill_map[sid] for sid in skill_ids if sid in skill_map]
    return enabled

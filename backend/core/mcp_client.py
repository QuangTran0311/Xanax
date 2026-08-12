"""Kết nối MCP server cấu hình qua giao diện CÔNG CỤ → + Thêm kỹ năng → Kết nối
nâng cao (MCP), rồi phơi từng tool của server đó thành tool thật trong
tool_registry để agent gọi được — song song với skill loại 'api' ở skill_tools.py.

Khác biệt cốt lõi so với skill 'api': một MCP server phơi ra NHIỀU tool, nên một
skill MCP nở ra thành N tool trong registry, đặt tên
`skill_mcp_<ten_skill>__<ten_tool_mcp>`.

Kết nối được giữ bền (persistent) chứ không mở/đóng theo từng lần gọi: server
stdio thường phải nạp model lúc khởi động (rembg mất ~4s nạp u2netp), mở lại mỗi
lần gọi sẽ biến tác vụ 0.4s thành 4.4s.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import shlex
from contextlib import asynccontextmanager
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from core.hermes.tool_registry import ToolDefinition, ToolParameter, tool_registry
from core.secret_crypto import decrypt_secret
from core.slugify import slugify

logger = logging.getLogger("xanax.tools.skill_mcp")

MCP_SKILL_PREFIX = "skill_mcp_"

# Thời gian chờ tối đa cho từng giai đoạn. MCP server bên thứ ba có thể treo hoặc
# tải model hàng chục MB lúc khởi động; không đặt trần thì cả app đứng theo.
_CONNECT_TIMEOUT = 90.0
_LIST_TIMEOUT = 30.0
_CALL_TIMEOUT = 300.0

# Nơi ghi ảnh do MCP tool trả về. Quy trình có thể trỏ sang thư mục archive của
# lần chạy (xem core/project_storage.get_or_create_run_dir) để ảnh nằm cùng chỗ
# với ảnh do image_gen sinh ra, thay vì rải rác.
MCP_IMAGE_DIR = Path(__file__).parent.parent / "data" / "mcp-images"
mcp_image_dir: ContextVar[str | None] = ContextVar("mcp_image_dir", default=None)

_MIME_EXT = {
    "image/png": ".png", "image/jpeg": ".jpg", "image/jpg": ".jpg",
    "image/webp": ".webp", "image/gif": ".gif",
}


def tool_prefix_for_skill(skill: dict) -> str:
    """Tiền tố tên tool ứng với 1 skill MCP — dùng chung giữa lúc đăng ký và lúc
    build tool schema cho agent."""
    return f"{MCP_SKILL_PREFIX}{slugify(skill['name']).replace('-', '_')}__"


def mcp_tool_short_names(skill: dict) -> list[str]:
    """Tên công cụ BÊN TRONG một MCP server, đã bỏ tiền tố của Xanax.

    Một skill MCP là cả một server phơi ra nhiều công cụ (cat_anh_san_pham có
    `cut_product` và `cut_product_batch`). Đây là danh sách để giao diện hiện ra
    cho Papa tích chọn từng cái.

    Đọc từ registry nên phải gọi sau `sync_mcp_skill_tools()`; server chưa kết nối
    được thì trả rỗng chứ không ném lỗi — giao diện lúc đó hiện nhóm không có con,
    đúng sự thật là chưa biết server có gì.
    """
    prefix = tool_prefix_for_skill(skill)
    return sorted(t.name[len(prefix):] for t in tool_registry.list_tools(tag="mcp")
                  if t.name.startswith(prefix))


def parse_skill_tools(agent: dict | None) -> dict[int, list[str]]:
    """Đọc cột `skill_tools_json` của nhân viên: {skill_id: [tên công cụ]}.

    Quy ước quan trọng: skill_id VẮNG MẶT trong map, hoặc có mà danh sách rỗng,
    đều nghĩa là LẤY HẾT công cụ của skill đó. Nhờ vậy mọi nhân viên tạo trước khi
    có tính năng này giữ nguyên hành vi cũ, và không cần migrate dữ liệu.

    Muốn nhân viên không dùng công cụ nào của một server thì bỏ chọn cả skill,
    đừng để danh sách rỗng.
    """
    if not agent:
        return {}
    try:
        raw = json.loads(agent.get("skill_tools_json") or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}
    if not isinstance(raw, dict):
        return {}

    out: dict[int, list[str]] = {}
    for key, names in raw.items():
        try:
            sid = int(key)
        except (TypeError, ValueError):
            continue
        if isinstance(names, list):
            picked = [str(n).strip() for n in names if str(n).strip()]
            if picked:
                out[sid] = picked
    return out


def filter_mcp_tool_names(tool_names: list[str], prefix: str, allowed: list[str] | None) -> list[str]:
    """Lọc tên tool đầy đủ theo danh sách công cụ được chọn của một skill MCP.

    `allowed` là tên ngắn (trong server gốc). None hoặc rỗng = không lọc.

    Tên được chọn mà server không còn phơi ra nữa thì tự rơi ra khỏi kết quả —
    server MCP đổi bộ công cụ là chuyện thường, và treo cứng theo tên đã lưu sẽ
    làm nhân viên mất luôn công cụ còn lại.
    """
    if not allowed:
        return tool_names
    keep = set(allowed)
    return [name for name in tool_names if name[len(prefix):] in keep]


def _split_command(target: str) -> tuple[str, list[str]]:
    """Tách chuỗi lệnh thành (command, args).

    Trên Windows phải dùng posix=False, nếu không shlex sẽ nuốt dấu `\` trong
    đường dẫn kiểu C:\\Users\\...\\rembg-mcp.exe và lệnh thành vô nghĩa.
    """
    if not target.strip():
        raise ValueError("Chưa nhập lệnh khởi chạy MCP server")
    if os.name == "nt":
        parts = [p.strip('"') for p in shlex.split(target, posix=False)]
    else:
        parts = shlex.split(target)
    if not parts:
        raise ValueError("Lệnh khởi chạy MCP server rỗng")
    return parts[0], parts[1:]


class MCPConnection:
    """Giữ một phiên MCP mở trong suốt vòng đời tiến trình.

    Context manager của SDK mcp phải được vào/ra trong cùng một task, nên phiên
    được giữ bởi một task giám sát chạy nền; các lời gọi tool đến từ task khác
    chỉ mượn lại `ClientSession` — đây là cách dùng bình thường của SDK vì
    ClientSession có vòng lặp nhận riêng.
    """

    def __init__(self, config_key: str, config: dict[str, Any]) -> None:
        self.config_key = config_key
        self.target: str = (config.get("target") or "").strip()
        self.transport: str = (config.get("transport") or "stdio").strip().lower()
        # Token lưu trong DB dạng đã mã hoá (xem core/secret_crypto.py) — giải mã
        # tại đây. Giá trị cũ chưa mã hoá được trả nguyên văn nên vẫn chạy.
        self.token: str = decrypt_secret(config.get("token") or "")
        self.env: dict[str, str] = {
            str(k): str(v) for k, v in (config.get("env") or {}).items()
        }
        self._session: Any = None
        self._ready = asyncio.Event()
        self._closing = asyncio.Event()
        self._task: asyncio.Task | None = None
        self.error: str | None = None
        self.tools: list[Any] = []

    # ── vòng đời ────────────────────────────────────────────────────────────

    @asynccontextmanager
    async def _open_session(self):
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        headers = {"Authorization": f"Bearer {self.token}"} if self.token else None

        if self.transport == "stdio":
            command, args = _split_command(self.target)
            params = StdioServerParameters(command=command, args=args, env=self.env or None)
            async with stdio_client(params) as (read, write):
                async with ClientSession(read, write) as session:
                    yield session
        elif self.transport == "http":
            from mcp.client.streamable_http import streamablehttp_client

            async with streamablehttp_client(self.target, headers=headers) as (read, write, _):
                async with ClientSession(read, write) as session:
                    yield session
        elif self.transport == "sse":
            from mcp.client.sse import sse_client

            async with sse_client(self.target, headers=headers) as (read, write):
                async with ClientSession(read, write) as session:
                    yield session
        else:
            raise ValueError(f"Transport MCP không hỗ trợ: {self.transport!r}")

    async def _run(self) -> None:
        try:
            async with self._open_session() as session:
                await session.initialize()
                self._session = session
                result = await session.list_tools()
                self.tools = list(result.tools)
                self.error = None
                self._ready.set()
                await self._closing.wait()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"
            logger.warning("MCP server %r lỗi: %s", self.target, self.error)
        finally:
            self._session = None
            # Luôn mở khoá người đang chờ, kể cả khi hỏng, để không treo vô hạn.
            self._ready.set()

    async def start(self) -> bool:
        """Khởi động và chờ tới khi phiên sẵn sàng. True nếu kết nối được."""
        if self._task is None or self._task.done():
            self._ready.clear()
            self._closing.clear()
            self.error = None
            self._task = asyncio.create_task(self._run(), name=f"mcp:{self.config_key}")
        try:
            await asyncio.wait_for(self._ready.wait(), timeout=_CONNECT_TIMEOUT)
        except asyncio.TimeoutError:
            self.error = f"Hết {_CONNECT_TIMEOUT:.0f}s chờ MCP server phản hồi"
            logger.warning("MCP server %r: %s", self.target, self.error)
            await self.close()
            return False
        return self._session is not None

    async def close(self) -> None:
        self._closing.set()
        task, self._task = self._task, None
        if task and not task.done():
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        self._session = None

    @property
    def alive(self) -> bool:
        return self._session is not None

    # ── gọi tool ────────────────────────────────────────────────────────────

    async def call_tool(self, name: str, args: dict) -> str:
        if not self.alive and not await self.start():
            return f"Không kết nối được MCP server: {self.error or 'lý do không rõ'}"
        try:
            result = await asyncio.wait_for(
                self._session.call_tool(name, args), timeout=_CALL_TIMEOUT,
            )
        except asyncio.TimeoutError:
            return f"Tool MCP {name!r} chạy quá {_CALL_TIMEOUT:.0f}s và bị huỷ"
        except Exception as exc:
            logger.exception("Gọi tool MCP %r thất bại", name)
            return f"Gọi tool MCP thất bại: {type(exc).__name__}: {exc}"

        text = _stringify_result(result)
        if getattr(result, "isError", False):
            return f"Lỗi từ MCP: {text}"
        return text


def _save_mcp_image(data_b64: str, mime: str) -> Path | None:
    """Ghi ảnh MCP trả về ra đĩa, trả về đường dẫn file.

    KHÔNG bao giờ đưa base64 vào text gửi cho model: output của model bị giới hạn
    vài trăm token nên nó không thể chép lại hàng chục nghìn ký tự — thay vào đó
    nó sẽ TỰ BỊA một chuỗi base64 trông giống thật, ra ảnh vỡ. Nhưng cũng không
    vứt ảnh đi: các tool của xanax làm việc theo ĐƯỜNG DẪN file (cut_product nhận
    input_path/output_path), nên lưu ra đĩa rồi đưa model đường dẫn là hợp nhất —
    model chuyển tiếp được sang tool khác, giao diện mở được, không qua LLM lần nào.
    """
    ext = _MIME_EXT.get((mime or "").lower(), ".png")
    target_dir = Path(mcp_image_dir.get() or MCP_IMAGE_DIR) / f"{datetime.now():%Y%m%d}"
    try:
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / f"{datetime.now():%H%M%S}_{uuid4().hex[:8]}{ext}"
        path.write_bytes(base64.b64decode(data_b64))
        return path
    except Exception:
        logger.exception("Không lưu được ảnh MCP trả về")
        return None


def _stringify_result(result: Any) -> str:
    """Gom nội dung trả về của MCP thành text cho model đọc."""
    parts: list[str] = []
    for item in getattr(result, "content", None) or []:
        kind = getattr(item, "type", None)
        if kind == "text":
            parts.append(getattr(item, "text", ""))
        elif kind == "image":
            mime = getattr(item, "mimeType", "image/png")
            saved = _save_mcp_image(getattr(item, "data", "") or "", mime)
            if saved:
                parts.append(
                    f"[đã nhận 1 ảnh ({mime}) và lưu tại: {saved}]\n"
                    "Dùng ĐÚNG đường dẫn này khi cần truyền ảnh sang tool khác. "
                    "TUYỆT ĐỐI không tự viết ra chuỗi base64 của ảnh."
                )
            else:
                parts.append(f"[nhận được 1 ảnh {mime} nhưng lưu ra đĩa thất bại]")
        elif kind == "resource":
            resource = getattr(item, "resource", None)
            parts.append(str(getattr(resource, "uri", "") or resource))
        else:
            parts.append(str(item))
    structured = getattr(result, "structuredContent", None)
    if not parts and structured is not None:
        try:
            parts.append(json.dumps(structured, ensure_ascii=False))
        except Exception:
            parts.append(str(structured))
    text = "\n".join(p for p in parts if p)
    return text[:4000] if len(text) > 4000 else text


def _params_from_input_schema(schema: dict | None) -> list[ToolParameter]:
    """Chuyển inputSchema (JSON Schema) của MCP sang ToolParameter của registry."""
    schema = schema or {}
    props: dict = schema.get("properties") or {}
    required: set = set(schema.get("required") or [])
    params: list[ToolParameter] = []
    for name, spec in props.items():
        spec = spec if isinstance(spec, dict) else {}
        json_type = spec.get("type")
        if isinstance(json_type, list):  # ví dụ ["string", "null"]
            json_type = next((t for t in json_type if t != "null"), "string")
        if not json_type:
            # oneOf/anyOf/enum không có type tường minh — mô tả tự do là đủ cho model.
            json_type = "string"
        params.append(ToolParameter(
            name=name,
            type=json_type,
            description=spec.get("description") or f"Tham số {name}",
            required=name in required,
            default=spec.get("default"),
        ))
    return params


class MCPManager:
    """Giữ các kết nối theo skill id và đồng bộ chúng với bảng skills."""

    def __init__(self) -> None:
        self._connections: dict[int, MCPConnection] = {}
        self._registered: dict[int, set[str]] = {}
        self._prefixes: dict[int, str] = {}
        # skill_id -> frozenset tên tool được chọn, hoặc None = lấy tất cả. Giữ
        # riêng khỏi config_key vì đổi lựa chọn KHÔNG cần dựng lại kết nối.
        self._selections: dict[int, frozenset[str] | None] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _config_key(config: dict) -> str:
        return json.dumps({
            "target": (config.get("target") or "").strip(),
            "transport": (config.get("transport") or "stdio").strip().lower(),
            "token": config.get("token") or "",
            "env": config.get("env") or {},
        }, sort_keys=True, ensure_ascii=False)

    def _unregister_skill(self, skill_id: int) -> None:
        for tool_name in self._registered.pop(skill_id, set()):
            tool_registry.unregister(tool_name)
        self._prefixes.pop(skill_id, None)
        self._selections.pop(skill_id, None)

    async def _drop(self, skill_id: int) -> None:
        self._unregister_skill(skill_id)
        conn = self._connections.pop(skill_id, None)
        if conn:
            await conn.close()

    async def sync(self, skills: list[dict]) -> None:
        """Đồng bộ toàn bộ skill loại 'mcp' đang bật thành tool trong registry."""
        async with self._lock:
            wanted: dict[int, dict] = {}
            for skill in skills:
                if skill.get("type") != "mcp" or not skill.get("enabled", 1):
                    continue
                try:
                    config = json.loads(skill.get("config_json") or "{}")
                except Exception:
                    logger.warning("Skill mcp %s có config_json không hợp lệ; bỏ qua", skill.get("id"))
                    continue
                if not (config.get("target") or "").strip():
                    continue
                wanted[skill["id"]] = {"skill": skill, "config": config}

            for skill_id in list(self._connections):
                if skill_id not in wanted:
                    await self._drop(skill_id)

            for skill_id, entry in wanted.items():
                await self._sync_one(skill_id, entry["skill"], entry["config"])

    async def _sync_one(self, skill_id: int, skill: dict, config: dict) -> None:
        key = self._config_key(config)
        conn = self._connections.get(skill_id)

        if conn is not None and conn.config_key != key:
            # Người dùng sửa target/transport/token → dựng lại kết nối.
            await self._drop(skill_id)
            conn = None

        # Danh sách tool được chọn ở tab CÔNG CỤ. Bỏ trống/không có = lấy tất cả
        # (giữ tương thích với skill tạo trước khi có tính năng chọn). Một MCP
        # server có thể phơi ra hàng chục tool; nhét hết vào schema thì mỗi lượt
        # gọi LLM của agent đều phải gánh toàn bộ, tốn token vô ích.
        # Phân biệt hai trạng thái KHÁC NHAU, không gộp:
        #   - không có khoá "tools"  → chưa từng chọn, lấy tất cả (tương thích ngược)
        #   - "tools": []            → đã chọn và bỏ hết, KHÔNG bật tool nào
        # Gộp chúng lại (coi mảng rỗng là falsy) thì người dùng bỏ chọn hết sẽ nhận
        # được đúng điều ngược lại với ý mình.
        raw_selected = config.get("tools")
        selected = (
            frozenset(str(n) for n in raw_selected)
            if isinstance(raw_selected, list) else None
        )

        if conn is not None and conn.alive:
            if self._selections.get(skill_id, "unset") == selected:
                return  # đã kết nối, đúng lựa chọn, tool đã đăng ký
            # Chỉ đổi danh sách tool chứ không đổi target/token: đăng ký lại từ
            # conn.tools đã có sẵn, KHÔNG dựng lại kết nối (server stdio phải nạp
            # model lại từ đầu, mất vài giây cho một thay đổi thuần cấu hình).
        else:
            if conn is None:
                conn = MCPConnection(key, config)
                self._connections[skill_id] = conn
            if not await conn.start():
                self._unregister_skill(skill_id)
                return

        prefix = tool_prefix_for_skill(skill)
        self._prefixes[skill_id] = prefix
        self._selections[skill_id] = selected

        names: set[str] = set()
        for mcp_tool in conn.tools:
            if selected is not None and mcp_tool.name not in selected:
                continue
            tool_name = f"{prefix}{slugify(mcp_tool.name).replace('-', '_')}"
            names.add(tool_name)
            tool_registry.register_tool(ToolDefinition(
                name=tool_name,
                description=(
                    f"{mcp_tool.description or mcp_tool.name} "
                    f"[MCP · {skill['name']} · tool gốc: {mcp_tool.name}]"
                ),
                parameters=_params_from_input_schema(
                    getattr(mcp_tool, "inputSchema", None),
                ),
                handler=_make_handler(conn, mcp_tool.name),
                is_async=True,
                tags=["skill", "mcp"],
            ))

        # Server có thể đã bỏ bớt tool giữa hai lần sync.
        for stale in self._registered.get(skill_id, set()) - names:
            tool_registry.unregister(stale)
        self._registered[skill_id] = names
        logger.info("MCP %r: đăng ký %d tool", skill["name"], len(names))

    def status(self) -> list[dict]:
        """Trạng thái từng kết nối — cho endpoint chẩn đoán."""
        return [
            {
                "skill_id": skill_id,
                "target": conn.target,
                "transport": conn.transport,
                "connected": conn.alive,
                "error": conn.error,
                # prefix để giao diện cắt ra tên tool gốc mà không phải nhân đôi
                # logic slugify (nó bỏ dấu tiếng Việt — rất dễ lệch).
                "prefix": self._prefixes.get(skill_id, ""),
                "tools": sorted(self._registered.get(skill_id, set())),
                # Toàn bộ tool server phơi ra, để giao diện hiện "đang bật N/M"
                # và biết còn tool nào chưa chọn.
                "available": [t.name for t in conn.tools],
            }
            for skill_id, conn in self._connections.items()
        ]

    async def close_all(self) -> None:
        async with self._lock:
            for skill_id in list(self._connections):
                await self._drop(skill_id)


def _make_handler(conn: MCPConnection, mcp_tool_name: str):
    async def handler(**kwargs: Any) -> str:
        # Bỏ tham số không truyền để server dùng default của chính nó.
        args = {k: v for k, v in kwargs.items() if v is not None}
        return await conn.call_tool(mcp_tool_name, args)

    handler.__name__ = f"mcp_{slugify(mcp_tool_name).replace('-', '_')}"
    return handler


mcp_manager = MCPManager()


async def sync_mcp_skill_tools() -> None:
    """Quét skill loại 'mcp' đang bật và đăng ký tool của chúng vào registry.

    Gọi song song với sync_api_skill_tools() ở mọi nơi registry cần tươi.
    """
    from hub.database import list_skills

    try:
        skills = await list_skills()
    except Exception:
        logger.exception("Không thể tải danh sách skill để đồng bộ mcp tool")
        return
    try:
        await mcp_manager.sync(skills)
    except Exception:
        logger.exception("Đồng bộ MCP tool thất bại")

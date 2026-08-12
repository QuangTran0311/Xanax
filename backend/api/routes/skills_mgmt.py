"""API Routes – Skill/tool management CRUD"""
import asyncio
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.secret_crypto import (
    decrypt_secret, encrypt_secret_config, mask_secret_config, merge_secret_config,
)
from hub.database import (
    list_skills, get_skill, create_skill, update_skill, delete_skill,
)
from hub.events import EventType, event_bus

router = APIRouter()


def _emit_data_changed():
    asyncio.create_task(event_bus.emit_simple(EventType.DATA_CHANGED, "skills"))


class SkillCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = Field("")
    type: str = Field("builtin")
    config: dict = Field(default_factory=dict)


class SkillUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    type: str | None = None
    config: dict | None = None
    enabled: int | None = None


def _raw_config(s: dict) -> dict:
    try:
        return json.loads(s.get("config_json") or "{}")
    except Exception:
        return {}


def _parse(s: dict) -> dict:
    """Config trả ra API — secret luôn bị che, không bao giờ trả giá trị thật."""
    s["config"] = mask_secret_config(_raw_config(s))
    return s


@router.get("/")
async def list_all_skills():
    skills = await list_skills()
    return {"skills": [_parse(s) for s in skills]}


@router.post("/", status_code=201)
async def create_new_skill(body: SkillCreate):
    skill_id = await create_skill(
        name=body.name,
        description=body.description,
        type_=body.type,
        config_json=json.dumps(encrypt_secret_config(body.config)),
    )
    skill = await get_skill(skill_id)
    _emit_data_changed()
    return _parse(skill)


class ConnectionTest(BaseModel):
    type: str
    config: dict = Field(default_factory=dict)
    # Skill đang sửa (nếu có). Form gửi secret dạng MASK, nên phải tra lại giá trị
    # thật từ DB thì mới test được kết nối của một skill đã lưu.
    skill_id: int | None = None


# Method có thể gây tác dụng phụ thật (đăng bài, tạo đơn...). Kiểm tra kết nối
# tuyệt đối không được gọi thật những method này — skill facebook_post_page dùng
# POST, bấm "kiểm tra" mà bắn POST là đăng bài lên Page thật.
_SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


async def _test_api_connection(config: dict) -> dict:
    import time

    import httpx

    endpoint = (config.get("endpoint") or "").strip()
    if not endpoint:
        return {"ok": False, "error": "Chưa nhập Endpoint URL"}
    method = (config.get("method") or "GET").upper()
    api_key = decrypt_secret(config.get("api_key") or "")
    headers = dict(config.get("headers") or {})
    if api_key and "Authorization" not in headers:
        headers["Authorization"] = f"Bearer {api_key}"

    executed = method in _SAFE_METHODS
    probe = method if executed else "HEAD"
    started = time.perf_counter()
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            response = await client.request(probe, endpoint, headers=headers)
    except Exception as exc:
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    elapsed = round((time.perf_counter() - started) * 1000)
    if executed:
        # Gọi thật method đã cấu hình nên status code phản ánh đúng kết quả.
        ok = response.status_code < 400
        note = f"Đã gọi thử {probe} {endpoint}"
    else:
        # Chỉ dò tới được server hay không. Status 4xx ở đây thường chỉ là do
        # HEAD thiếu tham số/token chứ không có nghĩa cấu hình sai, nên không
        # đánh trượt vì nó — nói rõ để người dùng tự đánh giá.
        ok = True
        note = (
            f"Server phản hồi (HTTP {response.status_code}) — đã tới được endpoint. "
            f"Không gọi thật {method} vì method này có thể thay đổi dữ liệu "
            f"(đăng bài, tạo đơn...), nên chưa kiểm chứng được token và tham số."
        )
    return {
        "ok": ok,
        "status_code": response.status_code,
        "elapsed_ms": elapsed,
        "executed": executed,
        "note": note,
    }


async def _test_mcp_connection(config: dict) -> dict:
    import time

    from core.mcp_client import MCPConnection

    if not (config.get("target") or "").strip():
        return {"ok": False, "error": "Chưa nhập địa chỉ / lệnh khởi chạy MCP server"}

    conn = MCPConnection("test-connection", config)
    started = time.perf_counter()
    try:
        ok = await conn.start()
        elapsed = round((time.perf_counter() - started) * 1000)
        return {
            "ok": ok,
            "error": conn.error,
            "elapsed_ms": elapsed,
            "tools": [
                {"name": t.name, "description": (t.description or "").strip()}
                for t in conn.tools
            ],
        }
    finally:
        # Kết nối thử phải đóng hẳn, nếu không mỗi lần bấm nút lại để lại một
        # tiến trình con MCP mồ côi.
        await conn.close()


@router.post("/test-connection", summary="Thử kết nối trước khi lưu skill")
async def test_connection(body: ConnectionTest):
    """Kiểm tra cấu hình kết nối mà không cần lưu skill trước.

    Với 'mcp' còn trả về danh sách tool mà server phơi ra, vì một MCP server
    thường có nhiều tool và người dùng cần thấy trước khi lưu.
    """
    config = body.config
    if body.skill_id is not None:
        current = await get_skill(body.skill_id)
        if current:
            config = merge_secret_config(config, _raw_config(current))

    if body.type == "mcp":
        return await _test_mcp_connection(config)
    if body.type == "api":
        return await _test_api_connection(config)
    raise HTTPException(400, f"Loại kết nối {body.type!r} không hỗ trợ kiểm tra")


@router.get("/{skill_id}")
async def get_one_skill(skill_id: int):
    skill = await get_skill(skill_id)
    if not skill:
        raise HTTPException(404, "Skill not found")
    return _parse(skill)


@router.get("/{skill_id}/tools", summary="Các công cụ bên trong một skill MCP")
async def list_skill_tools(skill_id: int):
    """Một skill MCP là cả một server phơi ra nhiều công cụ. Trả danh sách đó để
    giao diện gắn kỹ năng cho nhân viên hiện được từng công cụ mà tích chọn.

    Skill không phải loại 'mcp' thì trả danh sách rỗng — nó vốn là một công cụ
    đơn, chọn cả skill là xong, không có gì bên trong để chọn lẻ.
    """
    skill = await get_skill(skill_id)
    if not skill:
        raise HTTPException(404, "Skill not found")
    if skill.get("type") != "mcp":
        return {"skill_id": skill_id, "type": skill.get("type"), "tools": []}

    from core.hermes.tool_registry import tool_registry
    from core.mcp_client import mcp_tool_short_names, sync_mcp_skill_tools, tool_prefix_for_skill

    # Phải đồng bộ trước: danh sách công cụ nằm trong registry, mà registry chỉ
    # được nạp khi có ai đó chạy. Mở tab Nhân viên AI lúc server vừa khởi động mà
    # không gọi dòng này thì mọi nhóm MCP đều hiện ra rỗng.
    await sync_mcp_skill_tools()
    prefix = tool_prefix_for_skill(skill)
    tools = []
    for short in mcp_tool_short_names(skill):
        tool = tool_registry.get(prefix + short)
        tools.append({"name": short, "description": getattr(tool, "description", "") or ""})
    return {"skill_id": skill_id, "type": "mcp", "tools": tools}


@router.patch("/{skill_id}")
async def patch_skill(skill_id: int, body: SkillUpdate):
    kwargs = {}
    data = body.model_dump()
    if data.get("name") is not None:
        kwargs["name"] = data["name"]
    if data.get("description") is not None:
        kwargs["description"] = data["description"]
    if data.get("type") is not None:
        kwargs["type"] = data["type"]
    if data.get("config") is not None:
        # Form nhận secret dạng MASK; nếu người dùng không sửa ô đó thì phải giữ
        # giá trị đã lưu, nếu không mỗi lần bấm Lưu sẽ ghi đè token thật bằng
        # chuỗi dấu chấm.
        current = await get_skill(skill_id)
        if not current:
            raise HTTPException(404, "Skill not found")
        merged = merge_secret_config(data["config"], _raw_config(current))
        kwargs["config_json"] = json.dumps(encrypt_secret_config(merged))
    if data.get("enabled") is not None:
        kwargs["enabled"] = data["enabled"]
    ok = await update_skill(skill_id, **kwargs)
    if not ok:
        raise HTTPException(404, "Skill not found")
    skill = await get_skill(skill_id)
    _emit_data_changed()
    return _parse(skill)


@router.delete("/{skill_id}", status_code=204)
async def remove_skill(skill_id: int):
    ok = await delete_skill(skill_id)
    if not ok:
        raise HTTPException(404, "Skill not found")
    _emit_data_changed()

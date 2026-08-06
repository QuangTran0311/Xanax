"""
Cầu nối MCP — phơi kỹ năng loại 'api'/'builtin' của nhân viên Xanax cho CLI gói.

Vì sao cần
----------
Kỹ năng của nhân viên vốn được đưa cho model dưới dạng `tools[]` theo JSON
Schema. `claude` CLI không nhận dạng đó — nó chỉ nhận công cụ qua MCP. Không có
cầu nối này thì nhân viên chạy bằng gói thuê bao mất sạch khả năng hành động:
nó vẫn nói "đã đăng bài" trong khi không một request nào rời khỏi máy.

Phạm vi: CHỈ 'api' và 'builtin'
------------------------------
Kỹ năng loại 'mcp' vốn đã là một MCP server — `core/cli_provider.py` khai báo
thẳng nó cho CLI thay vì đi vòng qua đây. Proxy MCP-trong-MCP vừa thừa vừa hỏng:
mở phiên MCP con mất vài giây, đủ để CLI bỏ cuộc và báo server `pending`.

Chạy thế nào
------------
Không chạy tay. `core/cli_provider.py` sinh cấu hình `--mcp-config` trỏ vào đây:

    python mcp_servers/xanax_skills.py --skills 7

Lưu ý: stdio là kênh giao thức — TUYỆT ĐỐI không print ra stdout.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# File này chạy như tiến trình con do CLI spawn, cwd có thể là bất cứ đâu.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import mcp.types as types  # noqa: E402
from mcp.server.lowlevel import Server  # noqa: E402
from mcp.server.stdio import stdio_server  # noqa: E402

# Chuỗi mà handler skill 'api' trả về khi lời gọi hỏng (xem
# core/skill_tools.py:_make_api_skill_handler). Handler trả chuỗi thay vì ném
# lỗi, nên nếu cầu nối trả nguyên văn thì model đọc được "HTTP 400..." rồi vẫn
# có thể tự diễn giải thành "đã đăng xong". Đổi thành lỗi tool thật để CLI đánh
# dấu is_error và bước quy trình đọc được.
_FAILURE_PREFIXES = ("Lỗi từ API:", "HTTP ", "Gọi API thất bại:")


async def load_tool_names(skill_ids: list[int]) -> list[str]:
    """Đăng ký kỹ năng 'api'/'builtin' vào registry, trả về tên tool tương ứng."""
    from core.skill_tools import sync_api_skill_tools, tool_name_for_skill
    from hub.database import get_skill
    import tools as _builtin  # noqa: F401 — nạp tool builtin vào registry

    await sync_api_skill_tools()

    names: list[str] = []
    for sid in skill_ids:
        skill = await get_skill(sid)
        if not skill:
            continue
        kind = skill.get("type")
        if kind == "api":
            names.append(tool_name_for_skill(skill))
        elif kind == "builtin":
            try:
                config = json.loads(skill.get("config_json") or "{}")
            except (json.JSONDecodeError, TypeError):
                continue
            if config.get("tool_name"):
                names.append(config["tool_name"])

    seen: set[str] = set()
    return [n for n in names if not (n in seen or seen.add(n))]


async def _serve(skill_ids: list[int]) -> None:
    from core.hermes.tool_registry import tool_registry

    names = await load_tool_names(skill_ids)
    server = Server("xanax_skills")

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        out = []
        for name in names:
            tool = tool_registry.get(name)
            if tool is None:
                continue
            # to_schema() đã trả JSON Schema chuẩn của chính Xanax — dùng lại để
            # model thấy đúng tham số. Tự suy schema từ chữ ký hàm sẽ ra một ô
            # `kwargs` vô nghĩa, và model không biết phải truyền gì.
            schema = tool.to_schema()
            out.append(types.Tool(
                name=name,
                description=schema.get("description") or name,
                inputSchema=schema.get("parameters") or {"type": "object", "properties": {}},
            ))
        return out

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        result = await tool_registry.call(name, arguments or {})
        text = result if isinstance(result, str) else json.dumps(
            result, ensure_ascii=False, default=str
        )
        if isinstance(text, str) and text.startswith(_FAILURE_PREFIXES):
            # Ném lỗi để CLI đánh dấu is_error — im lặng trả chuỗi lỗi thì model
            # có thể diễn giải lại thành "đã xong".
            raise RuntimeError(text)
        return [types.TextContent(type="text", text=text)]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    parser = argparse.ArgumentParser(description="Cầu nối MCP cho kỹ năng Xanax")
    parser.add_argument("--skills", default="", help="Danh sách skill id, phân tách bằng dấu phẩy")
    args = parser.parse_args()

    skill_ids = [int(x) for x in args.skills.split(",") if x.strip().isdigit()]
    asyncio.run(_serve(skill_ids))


if __name__ == "__main__":
    main()

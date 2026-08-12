"""Chọn lẻ công cụ bên trong một skill MCP.

Một skill loại 'mcp' là cả một MCP server phơi ra nhiều công cụ. Trước đây gắn
skill đó cho nhân viên là nhân viên nhận HẾT; giờ chọn được từng cái.

Quy ước xuyên suốt (core/mcp_client.parse_skill_tools): skill không có trong map,
hoặc có mà danh sách rỗng, đều nghĩa là LẤY HẾT — nhờ vậy nhân viên tạo từ trước
không đổi hành vi. Muốn cắt sạch thì bỏ chọn cả skill.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.hermes.tool_registry import ToolDefinition, tool_registry
from core.mcp_client import (
    filter_mcp_tool_names, mcp_tool_short_names, parse_skill_tools, tool_prefix_for_skill,
)
from hub import database

_SKILL = {"id": 11, "name": "cat_anh_san_pham", "type": "mcp"}


def _register_fake_mcp_tools() -> str:
    """Giả lập một MCP server đã kết nối, phơi ra 3 công cụ."""
    prefix = tool_prefix_for_skill(_SKILL)
    for short in ("cut_product", "cut_product_batch", "describe_image"):
        tool_registry.register_tool(ToolDefinition(
            name=prefix + short, description=f"fake {short}",
            parameters=[], handler=lambda: None, tags=["mcp"],
        ))
    return prefix


def test_khong_chon_gi_thi_lay_het():
    assert parse_skill_tools({"skill_tools_json": "{}"}) == {}
    assert parse_skill_tools({"skill_tools_json": '{"11": []}'}) == {}, \
        "danh sách rỗng phải hiểu là lấy hết, không phải cấm hết"
    assert parse_skill_tools({}) == {}
    assert parse_skill_tools({"skill_tools_json": "hỏng"}) == {}
    assert parse_skill_tools({"skill_tools_json": '{"11": ["cut_product"]}'}) == {11: ["cut_product"]}


def test_loc_dung_cong_cu_da_chon():
    prefix = _register_fake_mcp_tools()
    names = [prefix + n for n in ("cut_product", "cut_product_batch", "describe_image")]

    assert filter_mcp_tool_names(names, prefix, None) == names
    assert filter_mcp_tool_names(names, prefix, []) == names
    assert filter_mcp_tool_names(names, prefix, ["cut_product"]) == [prefix + "cut_product"]
    # Tên đã lưu nhưng server không còn phơi ra thì rơi ra, không làm hỏng phần còn lại.
    assert filter_mcp_tool_names(names, prefix, ["cut_product", "da_bi_xoa"]) == [prefix + "cut_product"]


def test_liet_ke_cong_cu_trong_nhom():
    _register_fake_mcp_tools()
    assert mcp_tool_short_names(_SKILL) == ["cut_product", "cut_product_batch", "describe_image"]


async def test_build_agent_tools_chi_dung_cong_cu_da_chon(tmp_path, monkeypatch):
    """Đường model API: schema đưa cho model phải đúng bằng phần đã chọn."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "a.db"))
    await database.init_db()
    from api import websocket_workflow as wf

    # Tên khác hẳn test trên: tiền tố tool suy ra từ TÊN skill, mà tool_registry là
    # singleton dùng chung cả phiên chạy — trùng tên là dính tool của test khác.
    skill_id = await database.create_skill(
        name="cat_anh_build_tools", description="", type_="mcp", config_json="{}",
    )
    skill = {"id": skill_id, "name": "cat_anh_build_tools", "type": "mcp"}
    prefix = tool_prefix_for_skill(skill)
    for short in ("cut_product", "cut_product_batch"):
        tool_registry.register_tool(ToolDefinition(
            name=prefix + short, description=f"fake {short}",
            parameters=[], handler=lambda: None, tags=["mcp"],
        ))
    # sync_mcp_skill_tools sẽ đi kết nối server thật — chặn lại, registry đã có sẵn.
    monkeypatch.setattr("core.mcp_client.sync_mcp_skill_tools", _noop)

    everything = await wf._build_agent_tools([skill_id])
    assert {t["function"]["name"] if "function" in t else t["name"] for t in everything} == {
        prefix + "cut_product", prefix + "cut_product_batch",
    }

    only_one = await wf._build_agent_tools([skill_id], {skill_id: ["cut_product"]})
    names = {t["function"]["name"] if "function" in t else t["name"] for t in only_one}
    assert names == {prefix + "cut_product"}


async def _noop() -> None:
    return None


async def test_luu_lua_chon_va_bo_skill_khong_con_gan(tmp_path, monkeypatch):
    """Gỡ skill khỏi nhân viên thì lựa chọn công cụ của skill đó phải biến mất."""
    monkeypatch.setattr(database, "DB_PATH", str(tmp_path / "b.db"))
    await database.init_db()
    from api.routes.agent_configs import _clean_skill_tools

    assert json.loads(_clean_skill_tools({"11": ["cut_product"]}, [11])) == {"11": ["cut_product"]}
    assert json.loads(_clean_skill_tools({"11": ["cut_product"]}, [4])) == {}
    assert json.loads(_clean_skill_tools({"11": []}, [11])) == {}

    agent_id = await database.create_agent_config(
        name="Lexapro", skills_json=json.dumps([11, 4]),
        skill_tools_json=json.dumps({"11": ["cut_product"]}),
    )
    agent = await database.get_agent_config(agent_id)
    assert parse_skill_tools(agent) == {11: ["cut_product"]}

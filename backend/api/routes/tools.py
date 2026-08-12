"""API Routes – Tool registry management"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import tools as _registered_tools  # noqa: F401 - load decorator-based registrations
from core.hermes.tool_registry import tool_registry

router = APIRouter()


class CallToolRequest(BaseModel):
    name: str
    args: dict = {}


@router.get("/", summary="List all registered tools")
async def list_tools(tag: str | None = None):
    """List all tools available in the registry."""
    from core.mcp_client import sync_mcp_skill_tools
    from core.skill_tools import sync_api_skill_tools
    await sync_api_skill_tools()
    await sync_mcp_skill_tools()
    tools = tool_registry.list_tools(tag=tag)
    return {
        "total": len(tools),
        "tools": [t.to_schema() for t in tools],
    }


@router.get("/mcp/status", summary="MCP server connection status")
async def mcp_status():
    """Trạng thái từng MCP server cấu hình ở tab CÔNG CỤ — để chẩn đoán khi
    một skill MCP không hiện tool nào."""
    from core.mcp_client import mcp_manager, sync_mcp_skill_tools
    await sync_mcp_skill_tools()
    return {"servers": mcp_manager.status()}


@router.get("/{tool_name}", summary="Get tool schema")
async def get_tool(tool_name: str):
    """Get the schema for a specific tool."""
    tool = tool_registry.get(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{tool_name}' not found")
    return tool.to_schema()


@router.post("/call", summary="Call a tool directly")
async def call_tool(body: CallToolRequest):
    """Directly invoke a registered tool by name."""
    tool = tool_registry.get(body.name)
    if not tool:
        raise HTTPException(status_code=404, detail=f"Tool '{body.name}' not found")
    try:
        result = await tool_registry.call(body.name, body.args)
        return {"tool": body.name, "args": body.args, "result": result, "success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

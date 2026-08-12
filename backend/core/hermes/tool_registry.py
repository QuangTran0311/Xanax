"""
Hermes Tool Registry – Decorator-based dynamic tool registration & calling
"""
import asyncio
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class ToolParameter:
    name: str
    type: str
    description: str
    required: bool = True
    default: Any = None


@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: list[ToolParameter]
    handler: Callable
    is_async: bool = False
    tags: list[str] = field(default_factory=list)

    def to_schema(self) -> dict:
        """Return JSON-schema style tool description."""
        props = {}
        required = []
        for p in self.parameters:
            props[p.name] = {"type": p.type, "description": p.description}
            if p.default is not None:
                props[p.name]["default"] = p.default
            if p.required:
                required.append(p.name)

        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": props,
                "required": required,
            },
            "tags": self.tags,
        }


class ToolRegistry:
    """Central registry for all tools available to Hermes agents."""

    def __init__(self):
        self._tools: dict[str, ToolDefinition] = {}

    def register(
        self,
        name: str | None = None,
        description: str = "",
        tags: list[str] | None = None,
    ):
        """Decorator to register a function as a tool."""

        def decorator(fn: Callable) -> Callable:
            tool_name = name or fn.__name__
            is_async = asyncio.iscoroutinefunction(fn)

            # Auto-parse parameters from signature
            sig = inspect.signature(fn)
            hints = fn.__annotations__
            params = []
            for param_name, param in sig.parameters.items():
                if param_name in ("self", "ctx", "context"):
                    continue
                type_hint = hints.get(param_name, "string")
                type_str = _python_type_to_json(type_hint)
                has_default = param.default is not inspect.Parameter.empty
                params.append(
                    ToolParameter(
                        name=param_name,
                        type=type_str,
                        description=f"Parameter: {param_name}",
                        required=not has_default,
                        default=param.default if has_default else None,
                    )
                )

            tool_def = ToolDefinition(
                name=tool_name,
                description=description or (fn.__doc__ or "").strip(),
                parameters=params,
                handler=fn,
                is_async=is_async,
                tags=tags or [],
            )
            self._tools[tool_name] = tool_def
            return fn

        return decorator

    def register_tool(self, tool_def: ToolDefinition) -> None:
        """Directly register a ToolDefinition."""
        self._tools[tool_def.name] = tool_def

    def unregister(self, name: str) -> bool:
        """Gỡ tool khỏi registry. Dùng cho tool sinh động từ skill (MCP) khi
        skill bị xoá, bị tắt hoặc server đổi danh sách tool."""
        return self._tools.pop(name, None) is not None

    def get(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def list_tools(self, tag: str | None = None) -> list[ToolDefinition]:
        if tag:
            return [t for t in self._tools.values() if tag in t.tags]
        return list(self._tools.values())

    def get_schemas(self) -> list[dict]:
        return [t.to_schema() for t in self._tools.values()]

    async def call(self, name: str, args: dict | None = None) -> Any:
        """Call a registered tool by name."""
        tool = self._tools.get(name)
        if tool is None:
            raise ValueError(f"Tool '{name}' not found. Available: {list(self._tools.keys())}")

        args = args or {}
        try:
            if tool.is_async:
                result = await tool.handler(**args)
            else:
                result = await asyncio.to_thread(tool.handler, **args)
            return result
        except Exception as e:
            raise RuntimeError(f"Tool '{name}' failed: {e}") from e

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


def _python_type_to_json(hint: Any) -> str:
    """Map Python type hints to JSON schema types."""
    mapping = {
        "str": "string", "int": "integer", "float": "number",
        "bool": "boolean", "list": "array", "dict": "object",
        "Any": "string",
    }
    name = getattr(hint, "__name__", str(hint))
    return mapping.get(name, "string")


# Global tool registry
tool_registry = ToolRegistry()

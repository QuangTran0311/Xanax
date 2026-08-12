"""
Built-in Tools – Web Search, File Ops, Code Exec
All tools are registered on the global tool_registry.
"""
import asyncio
import os
import subprocess
from pathlib import Path

import httpx

from core.hermes.tool_registry import tool_registry


# ── Web Search ─────────────────────────────────────────────────────────────

@tool_registry.register(
    name="web_search",
    description="Search the web using DuckDuckGo Instant Answer API",
    tags=["web", "search"],
)
async def web_search(query: str) -> dict:
    """Search the web for a given query."""
    url = "https://api.duckduckgo.com/"
    params = {"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"}
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
    return {
        "abstract": data.get("Abstract", ""),
        "answer": data.get("Answer", ""),
        "url": data.get("AbstractURL", ""),
        "results": [
            {"title": r.get("Text", ""), "url": r.get("FirstURL", "")}
            for r in data.get("RelatedTopics", [])[:5]
            if isinstance(r, dict)
        ],
    }


# ── File Operations ────────────────────────────────────────────────────────

@tool_registry.register(
    name="read_file",
    description="Read the contents of a file",
    tags=["file", "io"],
)
async def read_file(path: str) -> str:
    """Read a file and return its contents."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    if not file_path.is_file():
        raise ValueError(f"Path is not a file: {path}")
    return file_path.read_text(encoding="utf-8")


@tool_registry.register(
    name="write_file",
    description="Write content to a file (creates if not exists)",
    tags=["file", "io"],
)
async def write_file(path: str, content: str) -> str:
    """Write content to a file."""
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return f"Successfully wrote {len(content)} characters to {path}"


@tool_registry.register(
    name="list_files",
    description="List files in a directory",
    tags=["file", "io"],
)
async def list_files(path: str = ".") -> list:
    """List files and directories in a given path."""
    dir_path = Path(path)
    if not dir_path.exists():
        raise FileNotFoundError(f"Directory not found: {path}")
    items = []
    for item in dir_path.iterdir():
        items.append({
            "name": item.name,
            "type": "directory" if item.is_dir() else "file",
            "size": item.stat().st_size if item.is_file() else None,
        })
    return sorted(items, key=lambda x: (x["type"] == "file", x["name"]))


@tool_registry.register(
    name="delete_file",
    description="Delete a file",
    tags=["file", "io"],
)
async def delete_file(path: str) -> str:
    """Delete a file at the given path."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    file_path.unlink()
    return f"Deleted: {path}"


# ── Code Execution ─────────────────────────────────────────────────────────

@tool_registry.register(
    name="run_python",
    description="Execute a Python code snippet and return stdout/stderr",
    tags=["code", "python"],
)
async def run_python(code: str, timeout: int = 10) -> dict:
    """Execute Python code in a subprocess."""
    process = await asyncio.create_subprocess_exec(
        "python", "-c", code,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        return {
            "stdout": stdout.decode("utf-8", errors="replace"),
            "stderr": stderr.decode("utf-8", errors="replace"),
            "return_code": process.returncode,
            "success": process.returncode == 0,
        }
    except asyncio.TimeoutError:
        process.kill()
        return {"error": f"Execution timed out after {timeout}s", "success": False}


@tool_registry.register(
    name="http_get_raw",
    description="Make an HTTP GET request and return raw response metadata",
    tags=["http", "web"],
)
async def http_get_raw(url: str, headers: dict | None = None) -> dict:
    """Perform an HTTP GET request."""
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
        resp = await client.get(url, headers=headers or {})
        return {
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "body": resp.text[:5000],  # Limit response size
            "success": resp.is_success,
        }


@tool_registry.register(
    name="get_system_info",
    description="Get current system information (CPU, memory, OS)",
    tags=["system"],
)
async def get_system_info() -> dict:
    """Return basic system information."""
    import platform
    import sys
    return {
        "os": platform.system(),
        "os_version": platform.version(),
        "python_version": sys.version,
        "cwd": os.getcwd(),
        "pid": os.getpid(),
    }

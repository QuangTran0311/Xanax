"""
Xanax - UI layer for Hermes local chat.
"""
import io
import sys
import threading
import webbrowser

import uvicorn
from rich.console import Console

from hub.config import settings
# Force UTF-8 output on Windows to handle box-drawing characters
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

console = Console(force_terminal=True, highlight=False)


def print_banner():
    name = settings.xanax_name
    version = settings.version
    host = settings.host
    port = settings.port

    console.print()
    console.print(f"  [bold magenta]{'━' * 52}[/]")
    console.print(f"  [bold white]  {name}[/] [dim]v{version}[/]  [dim]Hermes UI layer[/]")
    console.print(f"  [bold magenta]{'━' * 52}[/]")
    console.print()
    console.print(f"  [bold green]●[/] UI        [cyan]http://{host}:{port}/[/]")
    if settings.api_docs_enabled:
        console.print(f"  [bold green]●[/] API Docs  [cyan]http://{host}:{port}/api/docs[/]")
    console.print(f"  [bold green]●[/] Health    [cyan]http://{host}:{port}/api/health[/]")
    console.print()


def open_browser():
    """Tự mở trình duyệt tới trang UI sau khi server kịp khởi động.
    Set XANAX_NO_BROWSER=1 để tắt (vd chạy trên server không có màn hình)."""
    if settings.no_browser:
        return
    host = settings.host if settings.host not in ("0.0.0.0", "") else "localhost"
    url = f"http://{host}:{settings.port}/"
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()


def main():
    print_banner()
    open_browser()

    uvicorn.run(
        "hub.server:create_app",
        factory=True,
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level.lower(),
        reload=settings.debug,
        access_log=True,
    )


if __name__ == "__main__":
    main()

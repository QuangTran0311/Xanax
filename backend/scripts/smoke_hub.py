"""Playwright smoke test for the production React frontend.

Run the FastAPI server first, then execute ``python scripts/smoke_hub.py``.
The script creates a database session directly, visits all 12 Hub routes,
checks client-side navigation/state retention, and opens an archived image from
an old workflow run. Exit code 0 means the smoke checks passed.
"""

from __future__ import annotations

import asyncio
import io
import os
import pathlib
import sys
from urllib.parse import urlparse


if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

BASE = "http://localhost:8000"
TABS = [
    "home",
    "agents",
    "skills",
    "tasks",
    "meeting",
    "train",
    "company-runner",
    "auto-runner",
    "assets",
    "model",
    "cost",
    "settings",
]


async def main() -> int:
    import aiosqlite
    from playwright.async_api import async_playwright

    from hub.database import COOKIE_NAME, DB_PATH, create_session, init_db

    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        user = await (await db.execute("SELECT id, username FROM users LIMIT 1")).fetchone()

    if not user:
        print("KHÔNG có user nào trong DB — không đăng nhập được")
        return 2

    token = await create_session(user["id"])
    print(f"-- đăng nhập với user '{user['username']}' (id={user['id']})")

    errors: list[str] = []
    failed_requests: list[str] = []
    response_errors: list[str] = []
    hosts: set[str] = set()

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        context = await browser.new_context()
        await context.add_cookies(
            [{"name": COOKIE_NAME, "value": token, "domain": "localhost", "path": "/"}]
        )
        page = await context.new_page()

        page.on(
            "console",
            lambda message: errors.append(f"[console.error] {message.text}")
            if message.type == "error"
            else None,
        )
        page.on("pageerror", lambda error: errors.append(f"[pageerror] {error}"))
        page.on(
            "request",
            lambda request: hosts.add(urlparse(request.url).netloc),
        )
        page.on(
            "requestfailed",
            lambda request: failed_requests.append(f"{request.url} :: {request.failure}"),
        )
        page.on(
            "response",
            lambda response: response_errors.append(f"{response.status} {response.url}")
            if response.status >= 400
            and urlparse(response.url).hostname in {"localhost", "127.0.0.1"}
            else None,
        )

        response = await page.goto(f"{BASE}/hub", wait_until="networkidle", timeout=45_000)
        print(f"-- GET /hub -> {response.status if response else 'không có response'}")
        await page.locator('[data-hub-panel="home"]:not([hidden])').wait_for()

        print("-- 12 route Hub:")
        for tab in TABS:
            before = len(errors)
            path = "/hub" if tab == "home" else f"/hub/{tab}"
            try:
                await page.locator(f'a[href="{path}"]').click()
                await page.wait_for_url(f"{BASE}{path}")
                await page.locator(f'[data-hub-panel="{tab}"]:not([hidden])').wait_for()
                await page.wait_for_timeout(250)
            except Exception as error:
                errors.append(f"[{tab}] {error}")
            new_errors = len(errors) - before
            print(f"   {tab:14s} {'OK' if new_errors == 0 else f'{new_errors} LỖI'}")

        # React keeps every visited panel mounted. A search typed in Agents must
        # survive navigation away and back — behavior previously supplied by iframe.
        await page.locator('a[href="/hub/agents"]').click()
        agent_search = page.locator('[data-hub-panel="agents"] input[placeholder*="nhân viên"]')
        await agent_search.fill("__smoke_state__")
        await page.locator('a[href="/hub/skills"]').click()
        await page.locator('a[href="/hub/agents"]').click()
        retained = await agent_search.input_value() == "__smoke_state__"
        print(f"-- trạng thái tab cũ giữ nguyên: {'OK' if retained else 'HỎNG'}")
        if not retained:
            errors.append("chuyển tab làm mất state của tab Nhân sự")

        # Browser navigation must follow the same client-side route history.
        await page.locator('a[href="/hub/skills"]').click()
        await page.go_back()
        back_ok = page.url.endswith("/hub/agents")
        await page.go_forward()
        forward_ok = page.url.endswith("/hub/skills")
        print(f"-- Back/Forward: {'OK' if back_ok and forward_ok else 'HỎNG'}")
        if not back_ok or not forward_ok:
            errors.append("Back/Forward không khôi phục đúng route Hub")

        iframe_count = await page.locator("iframe").count()
        print(f"-- iframe trong DOM: {iframe_count}")
        if iframe_count:
            errors.append(f"còn {iframe_count} iframe trong DOM")

        # Open run #84 (2026-07-11) from the real history UI and let the browser
        # decode its archived image. This guards the 195-run legacy archive.
        await page.goto(f"{BASE}/taskrunner", wait_until="networkidle", timeout=45_000)
        await page.get_by_role("button", name="Tác vụ tự động").click()
        task_card = page.locator('[data-task-id="1"]')
        await task_card.wait_for()
        await task_card.get_by_role("button", name="Lịch sử").click()
        await page.get_by_text("#84", exact=True).click()
        old_image = page.locator(
            'img[src*="/api/workflow/runs/84/archive-file?path=02_lexapro.png"]'
        )
        await old_image.wait_for()
        image_ok = await old_image.evaluate(
            """image => new Promise((resolve) => {
              const decoded = () => resolve(
                image.naturalWidth > 0 && image.naturalHeight > 0
              );
              if (image.complete) return decoded();
              image.addEventListener("load", decoded, { once: true });
              image.addEventListener("error", () => resolve(false), { once: true });
            })"""
        )
        print(f"-- ảnh run cũ #84 hiển thị: {'OK' if image_ok else 'HỎNG'}")
        if not image_ok:
            errors.append("ảnh archive của run cũ #84 không giải mã/hiển thị được")

        # Login is public and must render as the React login page for an anonymous context.
        anonymous = await browser.new_context()
        login_page = await anonymous.new_page()
        anonymous_errors: list[str] = []
        login_page.on("pageerror", lambda error: anonymous_errors.append(str(error)))
        login_response = await login_page.goto(
            f"{BASE}/login", wait_until="networkidle", timeout=45_000
        )
        has_form = await login_page.locator('input[type="password"]').count() == 1
        print(
            f"-- /login -> {login_response.status if login_response else 'n/a'}: "
            f"{'OK' if has_form and not anonymous_errors else 'HỎNG'}"
        )
        if not has_form:
            errors.append("/login không dựng được form đăng nhập React")
        errors.extend(f"[anonymous] {error}" for error in anonymous_errors)
        await anonymous.close()

        await browser.close()

    local_failed = [
        failure
        for failure in failed_requests
        if urlparse(failure.split(" :: ", 1)[0]).hostname in {"localhost", "127.0.0.1"}
        and "ERR_ABORTED" not in failure
    ]
    external_hosts = sorted(host for host in hosts if not host.startswith(("localhost", "127.0.0.1")))
    print(f"-- hosts đã gọi: {', '.join(sorted(hosts)) or '(không có)'}")
    print(f"-- hosts ngoài máy: {', '.join(external_hosts) or '(không có)'}")

    if errors:
        print(f"\n=== {len(errors)} LỖI TRÌNH DUYỆT ===")
        for error in dict.fromkeys(errors):
            print(f"  {error[:500]}")
    if local_failed:
        print(f"\n=== {len(local_failed)} REQUEST LOCAL HỎNG ===")
        for failure in local_failed:
            print(f"  {failure}")
    if response_errors:
        print(f"\n=== {len(response_errors)} RESPONSE LOCAL >= 400 ===")
        for failure in dict.fromkeys(response_errors):
            print(f"  {failure}")

    ok = not errors and not local_failed and not response_errors
    print(f"\n=== {'SMOKE XANH' if ok else 'SMOKE HỎNG'} ===")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))

"""Smoke test trang /hub: nạp thật bằng Chromium, đi qua từng tab, thu lỗi.

Vì sao cần
----------
Frontend không có test. Lỗi ES module (thiếu export, tham chiếu chéo sót) và
handler nội tuyến chết lặng đều chỉ lộ lúc chạy trong trình duyệt, không có
công cụ tĩnh nào bắt được. Script này là lưới an toàn cho mọi thay đổi trong
dashboard/static/hub/.

Chạy
----
    python main.py                # cửa sổ khác, để server lên trước
    python scripts/smoke_hub.py   # thoát 0 = sạch

Không nằm trong pytest vì cần server sống + Chromium của Playwright
(cài một lần: `playwright install chromium`).

Đăng nhập bằng cách tạo session thẳng trong DB, nên không cần biết mật khẩu.
"""
import asyncio, sys, os, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

BASE = "http://localhost:8000"
TABS = ["home", "agents", "skills", "tasks", "ops", "knowledge",
        "meetings", "models", "cost", "assets", "benchmark", "settings"]


async def main():
    from hub.database import init_db, create_session, COOKIE_NAME, get_user_by_username
    import aiosqlite
    from hub.database import DB_PATH

    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        row = await (await db.execute("SELECT id, username FROM users LIMIT 1")).fetchone()
    if not row:
        print("KHÔNG có user nào trong DB — không đăng nhập được"); return 2
    token = await create_session(row["id"])
    print(f"-- đăng nhập với user '{row['username']}' (id={row['id']})")

    from playwright.async_api import async_playwright
    errors, failed_req = [], []

    async with async_playwright() as p:
        browser = await p.chromium.launch()
        ctx = await browser.new_context()
        await ctx.add_cookies([{"name": COOKIE_NAME, "value": token,
                                "domain": "localhost", "path": "/"}])
        page = await ctx.new_page()
        page.on("console", lambda m: errors.append(f"[console.{m.type}] {m.text}")
                if m.type in ("error",) else None)
        page.on("pageerror", lambda e: errors.append(f"[pageerror] {e}"))
        page.on("requestfailed", lambda r: failed_req.append(f"{r.url} :: {r.failure}"))

        resp = await page.goto(f"{BASE}/hub", wait_until="networkidle", timeout=45000)
        print(f"-- GET /hub -> {resp.status}")

        # Module đã nạp chưa: cầu window.* phải có mặt
        bridged = await page.evaluate("typeof window.switchTab === 'function'")
        print(f"-- cầu window.switchTab: {'OK' if bridged else 'THIẾU'}")
        # Mọi handler nội tuyến trong hub.html phải có mặt trên window, nếu không
        # nút bấm sẽ chết lặng (ReferenceError chỉ nổ lúc người dùng click).
        import re as _re
        html = (ROOT / "dashboard" / "hub.html").read_text(encoding="utf-8")
        wanted = sorted({nm for mt in _re.finditer(
            r'on(?:click|change|input|submit|keydown|keyup|blur|focus)="([^"]*)"', html)
            for nm in _re.findall(r"\b([A-Za-z_$][\w$]*)\s*\(", mt.group(1))})
        missing_h = await page.evaluate(
            "names => names.filter(n => typeof window[n] !== 'function')", wanted)
        # bỏ qua phương thức DOM gọi trên this/biến (vd this.remove(), e.stopPropagation())
        dom_ish = {"remove", "stopPropagation", "click", "getElementById",
                   "replace", "stringify", "if", "preventDefault", "focus", "blur"}
        missing_h = [m for m in missing_h if m not in dom_ish]
        print(f"-- handler nội tuyến trong hub.html: {len(wanted)} tên, "
              f"thiếu {len(missing_h)}")
        if missing_h:
            print("   THIẾU: " + ", ".join(missing_h))
            errors.append("handler thiếu trên window: " + ", ".join(missing_h))

        for tab in TABS:
            before = len(errors)
            try:
                await page.evaluate(f"window.switchTab('{tab}')")
                await page.wait_for_timeout(900)
            except Exception as e:
                errors.append(f"[switchTab {tab}] {e}")
            new = len(errors) - before
            print(f"   tab {tab:11s} {'OK' if new == 0 else f'{new} LỖI'}")

        await browser.close()

    print()
    if errors:
        print(f"=== {len(errors)} LỖI ===")
        seen = set()
        for e in errors:
            if e[:160] in seen: continue
            seen.add(e[:160]); print("  " + e[:300])
    else:
        print("=== KHÔNG có lỗi console/page ===")

    real_fail = [f for f in failed_req if "/static/" in f or "/api/" in f]
    if real_fail:
        print(f"\n=== {len(real_fail)} REQUEST HỎNG ===")
        for f in real_fail[:15]: print("  " + f)

    return 1 if (errors or real_fail) else 0


sys.exit(asyncio.run(main()))

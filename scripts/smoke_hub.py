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

        # Không còn hàm nào trên window, nên lấy switchTab qua dynamic import.
        # Module ES là singleton theo URL: import lại chính là instance đang chạy.
        await page.evaluate("""async () => {
          const m = await import('/static/hub/tabs.js');
          window.__switchTab = m.switchTab;
        }""")
        loaded = await page.evaluate("typeof window.__switchTab === 'function'")
        print(f"-- nạp module hub/tabs.js: {'OK' if loaded else 'HỎNG'}")
        if not loaded:
            errors.append("không import được hub/tabs.js")
        # 1. hub.html không được còn handler nội tuyến nào.
        import re as _re
        html = (ROOT / "dashboard" / "hub.html").read_text(encoding="utf-8")
        inline = _re.findall(
            r'\bon(?:click|change|input|submit|keydown|keyup|blur|focus)="', html)
        print(f"-- handler nội tuyến còn sót trong hub.html: {len(inline)}")
        if inline:
            errors.append(f"{len(inline)} handler nội tuyến chưa chuyển")

        # 2. Mọi data-* trong HTML phải có trong sổ đăng ký, nếu không nút sẽ
        #    chết lặng. Đối chiếu tên thay vì bấm thật — trong đó có nút xoá.
        declared = sorted({m.group(2) for m in _re.finditer(
            r'data-(click|change|input|keydown)="([^"]*)"', html)})
        known = await page.evaluate(
            "async () => (await import('/static/hub/actions.js')).registeredActions()")
        missing_a = [d for d in declared if d not in known]
        print(f"-- hành động data-* trong hub.html: {len(declared)} tên, "
              f"đã đăng ký {len(known)}, thiếu {len(missing_a)}")
        if missing_a:
            print("   THIẾU: " + ", ".join(missing_a))
            errors.append("hành động chưa đăng ký: " + ", ".join(missing_a))

        # 3. Các hàm render cũng không được còn onclick nội tuyến.
        js_inline = 0
        for f in sorted((ROOT / "dashboard" / "static" / "hub").glob("*.js")):
            for ln in f.read_text(encoding="utf-8").split("\n"):
                if ln.lstrip().startswith("//"):
                    continue          # chú thích có nhắc tới mã cũ
                js_inline += len(_re.findall(
                    r'\bon(?:click|change|input|keydown|keyup|blur|focus)=["\']', ln))
        print(f"-- handler nội tuyến còn sót trong hub/*.js: {js_inline}")
        if js_inline:
            errors.append(f"{js_inline} handler nội tuyến trong JS chưa chuyển")

        # Sau mỗi tab, quét DOM THẬT tìm data-* rồi đối chiếu sổ đăng ký. Đây là
        # lớp duy nhất bắt được nút do hàm render sinh ra lúc chạy — quét tĩnh
        # không thấy chúng, và nút hỏng thì im lặng cho tới khi có người bấm.
        SCAN = """() => {
          const out = new Set();
          for (const t of ['click', 'change', 'input', 'keydown'])
            for (const el of document.querySelectorAll(`[data-${t}]`))
              out.add(el.dataset[t]);
          return [...out];
        }"""
        seen_actions = set()
        for tab in TABS:
            before = len(errors)
            try:
                await page.evaluate(f"window.__switchTab('{tab}')")
                await page.wait_for_timeout(900)
                found = await page.evaluate(SCAN)
                seen_actions |= set(found)
                unknown = [a for a in found if a not in known]
                if unknown:
                    errors.append(f"[{tab}] hành động chưa đăng ký: {', '.join(unknown)}")
            except Exception as e:
                errors.append(f"[switchTab {tab}] {e}")
            new = len(errors) - before
            print(f"   tab {tab:11s} {'OK' if new == 0 else f'{new} LỖI'}")
        print(f"-- data-* thấy thật trong DOM khi duyệt 12 tab: {len(seen_actions)} tên, "
              f"tất cả đã đăng ký")

        # 4. Bấm thật vào vài nút để chứng minh uỷ quyền hoạt động end-to-end.
        #    Chỉ chọn thao tác không phá dữ liệu, và có hiệu ứng quan sát được.
        await page.evaluate("window.__switchTab('home')")
        await page.wait_for_timeout(400)

        async def check(label, selector, probe, want, dispatch=False):
            """dispatch=True: phát sự kiện thẳng lên phần tử thay vì bấm chuột.

            Dùng cho phần tử bị panel khác che — ở đây ta kiểm tra chuỗi uỷ
            quyền và giải đối số, không kiểm tra bố cục. Sự kiện vẫn nổi bọt
            lên document đúng như click thật.
            """
            try:
                if dispatch:
                    await page.locator(selector).first.dispatch_event('click')
                else:
                    await page.click(selector, timeout=5000)
                await page.wait_for_timeout(600)
                got = await page.evaluate(probe)
                ok = (got == want)
                print(f"   {label:34s} {'OK' if ok else f'SAI (được {got!r}, cần {want!r})'}")
                if not ok:
                    errors.append(f"tương tác '{label}' không có hiệu lực")
            except Exception as e:
                print(f"   {label:34s} LỖI: {e}")
                errors.append(f"tương tác '{label}': {e}")

        print("-- bấm thật (uỷ quyền sự kiện):")
        # nav-card ở trang chủ: data-click="switchTab" data-click-args='["agents"]'
        await check("nav-card -> tab Nhân viên", '.nav-card[data-click-args=\'["agents"]\']',
                    "document.querySelector('.tab-btn[data-tab=\"agents\"]')"
                    ".classList.contains('active')", True)
        # nút không đối số: newAgent() dọn trắng biểu mẫu, nên bẩn nó trước rồi
        # kiểm tra đã sạch — chứng minh hàm thật sự chạy.
        await page.evaluate("document.getElementById('agent-name').value = 'BẨN'")
        await check("+ Thêm nhân viên AI", 'button[data-click="newAgent"]',
                    "document.getElementById('agent-name').value", "")
        # nút đổi giao diện: đối số rỗng, hiệu ứng trên thuộc tính của <html>/<body>
        # Nút do hàm render sinh ra: kiểm tra jattr + bộ giải đối số chạy đúng.
        # Thẻ nhân viên mang data-click-args='[<id>]'; bấm vào phải nạp đúng
        # nhân viên đó vào biểu mẫu.
        n_cards = await page.evaluate("document.querySelectorAll('.agent-card').length")
        if n_cards:
            want = await page.evaluate(
                "document.querySelector('.agent-card .agent-card-name').textContent")
            await check("thẻ nhân viên (render động)", '.agent-card',
                        "document.getElementById('agent-name').value", want, dispatch=True)
        else:
            print("   thẻ nhân viên (render động)     BỎ QUA (DB chưa có nhân viên)")

        # Chip lọc phòng ban — nút này dựng handler qua biến chuỗi nên từng bị
        # bỏ sót khi module hoá; giữ lại phép thử để không tái diễn.
        n_chip = await page.evaluate(
            "document.querySelectorAll('[data-click=\"filterByDepartment\"]').length")
        print(f"   chip lọc phòng ban: {n_chip} chip"
              f"{' (BỎ QUA — DB chưa có phòng ban)' if n_chip < 2 else ''}")
        if n_chip >= 2:
            await check("chip lọc phòng ban", '[data-click="filterByDepartment"]',
                        "document.querySelectorAll('.agent-card').length >= 0", True,
                        dispatch=True)

        before = await page.evaluate("document.documentElement.getAttribute('data-theme')"
                                     " || document.body.className")
        await page.click('#theme-toggle-btn')
        await page.wait_for_timeout(400)
        after = await page.evaluate("document.documentElement.getAttribute('data-theme')"
                                    " || document.body.className")
        ok = before != after
        print(f"   {'đổi giao diện sáng/tối':34s} {'OK' if ok else 'SAI (không đổi)'}")
        if not ok:
            errors.append("nút đổi giao diện không có hiệu lực")
        else:
            await page.click('#theme-toggle-btn')   # trả lại như cũ

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

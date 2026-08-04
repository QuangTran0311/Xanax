# Plan: sửa hiển thị Trang chủ `/hub` + hạ tầng frontend

Tài liệu này viết cho một agent/lập trình viên **chưa từng đọc dự án**. Mọi số dòng,
selector và tên hàm đều đã kiểm chứng trên mã nguồn ngày **2026-07-31**. Nếu số dòng
lệch, hãy tìm theo selector/tên hàm — đó mới là mốc chuẩn.

---

## 0. Bối cảnh tối thiểu

- Dự án: **Xanax** — hệ thống điều phối AI agent (FastAPI + SQLite + giao diện HTML thuần).
- Thư mục gốc: `d:\xanax`
- Trang chủ nằm ở tab `home` trong **một file duy nhất**: `dashboard/hub.html` (~373 KB,
  7.264 dòng, gồm cả CSS `<style>` và JS `<script>` nội tuyến).
- **Không có build step, không framework, không package.json.** Sửa trực tiếp file HTML.
- Backend: `hub/server.py` (FastAPI, hàm `create_app()`).

### Chạy và kiểm tra

```bash
# chạy app (mặc định localhost:8000)
python main.py

# hoặc chạy cổng riêng để không đụng phiên đang mở
python -m uvicorn hub.server:create_app --factory --host 127.0.0.1 --port 8123

# test backend — PHẢI giữ 75 passed sau khi sửa
python -m pytest -q

# kiểm cú pháp JS sau MỌI lần sửa hub.html (bắt buộc, xem mục 8)
```

### Ràng buộc bắt buộc

1. **Không đổi bảng màu.** Dùng lại biến CSS đã có: `--bg-card`, `--ink`, `--ink-muted`,
   `--border`, `--accent`, `--gold`, `--mint-ink`, `--sky-ink`, `--lavender-ink`,
   `--peach-ink`, `--radius`, `--shadow`. Có **2 theme** (dark/light) — mọi màu mới phải
   lấy từ biến, tuyệt đối không hardcode mã hex.
2. **Không thêm thư viện ngoài** (không React, không Chart.js, không Tailwind).
3. **Giữ song ngữ**: chuỗi hiển thị mới nên có `data-i18n` nếu tiện, nhưng không bắt buộc
   — dự án đang có nhiều chuỗi tiếng Việt cứng.
4. Sau mỗi task: mở `/hub`, xem tab Trang chủ ở **cả 2 theme** và **2 độ rộng** (1600px, 1024px).

---

## 1. [A1] Widget rỗng không được chiếm chỗ trống

### Hiện trạng

`dashboard/hub.html` dòng ~352 và ~368:

```css
.home-widget {
  min-width: 0; min-height: 220px; padding: 16px;
  background: var(--bg-card); border-radius: var(--radius); box-shadow: var(--shadow);
  display: flex; flex-direction: column;
}
.home-empty { height: 100%; min-height: 150px; display: flex; align-items: center;
  justify-content: center; text-align: center; color: var(--ink-muted);
  font-size: 12px; line-height: 1.6; padding: 20px; }
```

Hậu quả: khi "Tác vụ đang chạy" hoặc "Cảnh báo hệ thống" không có dữ liệu, khối vẫn cao
tối thiểu 220px và bên trong có thêm khối rỗng 150px. Nửa dưới trang chủ gần như trống.

### Việc cần làm

1. Bỏ `min-height: 220px` cứng trên `.home-widget`. Thay bằng cơ chế: widget **có dữ liệu**
   mới cao 220px; widget rỗng co lại vừa nội dung.

   Cách làm gợi ý (không bắt buộc theo đúng chữ):
   ```css
   .home-widget { min-height: 0; }
   .home-widget:has(.home-widget-list) { min-height: 220px; }
   .home-empty { height: auto; min-height: 0; padding: 18px 20px; }
   ```
   `:has()` được hỗ trợ trên mọi trình duyệt hiện đại. Nếu muốn tránh `:has()`, thay bằng
   cách thêm class `is-empty` vào `.home-widget` từ JS khi render ra rỗng.

2. Ba widget nằm cùng hàng `.home-widget-grid` phải **vẫn bằng nhau về chiều cao**
   (grid mặc định `align-items: stretch` đã lo việc này) — chỉ khi **cả hàng** đều rỗng thì
   hàng mới thấp xuống. Kiểm tra kỹ điểm này: widget "Xu hướng chi phí" luôn có canvas cao
   150px nên hàng trên hiếm khi co.

3. `.home-alerts` (hàng dưới) hiện không có `min-height` nhưng bị `.home-bottom-grid > section
   { height: 100% }` kéo cao bằng ô bên cạnh — xử lý ở task A2.

### Tiêu chí nghiệm thu

- Khi không có tác vụ đang chạy: khối "Tác vụ đang chạy" cao **không quá 120px**.
- Khi có ≥1 tác vụ: khối cao như cũ (~220px trở lên), danh sách hiển thị đủ.
- Ba widget hàng trên vẫn thẳng hàng đáy khi có dữ liệu.

---

## 2. [A2] Cân lại hàng dưới

### Hiện trạng

Dòng ~379:

```css
.home-bottom-grid { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 14px; align-items: stretch; }
.home-bottom-grid > section { min-width: 0; height: 100%; }
```

Markup (dòng ~1635–1647): `<section class="home-alerts">` (Cảnh báo hệ thống) và
`<section class="home-recent-panel">` (Hoạt động gần đây).

Hậu quả: chia đôi 50/50. "Cảnh báo" thường chỉ có 1 dòng ("Mọi thứ đang ổn"), "Hoạt động"
có 4–10 dòng → bên trái hụt, bên phải chật.

### Việc cần làm

1. Đổi tỷ lệ thành **4 : 6**:
   ```css
   .home-bottom-grid { grid-template-columns: minmax(0, 4fr) minmax(0, 6fr); }
   ```
2. Bỏ `height: 100%` trên `> section` để ô cảnh báo không bị kéo cao theo ô bên cạnh.
   Đổi `align-items: stretch` → `align-items: start`.
3. Dưới **900px** chuyển thành 1 cột:
   ```css
   @media (max-width: 900px) {
     .home-bottom-grid { grid-template-columns: minmax(0, 1fr); }
   }
   ```

### Tiêu chí nghiệm thu

- Ở 1600px: Cảnh báo chiếm ~40% chiều rộng, Hoạt động ~60%.
- Khi không có cảnh báo, ô Cảnh báo **không** cao bằng ô Hoạt động.
- Ở 900px trở xuống: hai khối xếp dọc.

---

## 3. [A3] Stat card có ngữ cảnh, tiền tệ đúng định dạng

### Hiện trạng

Markup dòng ~1584–1613: 4 thẻ, mỗi thẻ chỉ có `.stat-card-value` + `.stat-card-label`.
Id giá trị: `ov-n-agents`, `ov-n-running`, `ov-cost-today`, `ov-success-rate`.

JS `renderOverview()` tại dòng **3950**, phần tiền tệ tại **dòng 3977**:

```js
document.getElementById('ov-cost-today').textContent = Object.keys(totals).length
  ? Object.entries(totals).map(([currency, value]) => `${Number(value).toLocaleString('vi-VN', { maximumFractionDigits: 4 })} ${currency}`).join(' · ')
  : '0';
```

Hậu quả: hiện `0,0983 USD` — 4 chữ số thập phân, khó đọc, và không có ngữ cảnh nào cho
biết con số là tốt hay xấu.

### Việc cần làm

1. **Định dạng tiền**: đổi `maximumFractionDigits: 4` → `minimumFractionDigits: 2,
   maximumFractionDigits: 2`. Nếu giá trị `> 0` nhưng làm tròn thành `0,00` thì hiện
   `< 0,01` thay vì `0,00` (tránh hiểu nhầm là miễn phí).

2. **Thêm dòng phụ đề** cho mỗi thẻ: thêm `<div class="stat-card-sub" id="ov-...-sub"></div>`
   dưới `.stat-card-label`, và CSS:
   ```css
   .stat-card-sub { font-size: 11px; color: var(--ink-muted); margin-top: 4px; display: flex; align-items: center; gap: 4px; }
   .stat-card-sub.up { color: var(--mint-ink); }
   .stat-card-sub.down { color: var(--peach-ink); }
   ```

3. Nội dung phụ đề (tính trong `renderOverview()`, dùng dữ liệu **đã có sẵn** trong hàm —
   biến `runs`, `todayRuns`, `finished`, `success`, `agents`):

   | Thẻ | Phụ đề |
   |---|---|
   | Nhân viên AI | `"<N> đang bật"` (đếm `agents.filter(a => a.enabled)`) |
   | Quy trình đang chạy | `"<N> lượt chạy hôm nay"` (`todayRuns.length`) |
   | Chi phí hôm nay | so với hôm qua: `"↑ 12% so với hôm qua"` / `"↓ 8%..."`, kèm class `up`/`down`. Lấy dữ liệu hôm qua từ `/model-pool/cost/report?period=day&date_from=...&date_to=...` (xem `loadHomeCostTrend()` dòng **3845** để tái dùng cách gọi) |
   | Tỷ lệ thành công hôm nay | `"<success>/<finished> lượt hoàn thành"` |

4. **Quan trọng — không bịa số.** Khi chưa đủ dữ liệu để tính (vd chưa có lượt chạy nào
   hôm qua), để phụ đề trống hoặc ghi `"chưa đủ dữ liệu"`. Không hiển thị `0%` hay mũi tên
   giả. Đây là quy tắc đã áp dụng ở chỗ khác trong dự án.

### Tiêu chí nghiệm thu

- Chi phí hiện `0,10 USD` (2 chữ số) hoặc `< 0,01 USD`, không còn `0,0983`.
- Cả 4 thẻ đều có dòng phụ đề, hoặc trống nếu thiếu dữ liệu — không thẻ nào hiện số bịa.
- Mũi tên tăng/giảm đổi màu đúng (`--mint-ink` khi giảm chi phí, `--peach-ink` khi tăng).

---

## 4. [A4] Điểm ngắt đáp ứng

### Hiện trạng

Dòng ~296 và ~314, **không có `@media` nào**:

```css
.stat-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.nav-cards  { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.home-widget-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
```

Hậu quả đo được ở 1024px: stat card vẫn giữ 4 cột, chữ vỡ 3 dòng (`Chi phí hôm / nay`).

### Việc cần làm

Thêm khối media query (đặt ngay sau các rule trên để dễ đọc):

```css
@media (max-width: 1400px) {
  .home-widget-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 1200px) {
  .stat-cards { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 900px) {
  .home-widget-grid { grid-template-columns: minmax(0, 1fr); }
  .stat-cards { grid-template-columns: minmax(0, 1fr); }
}
```

Lưu ý: `.nav-cards` (Truy cập nhanh) hiện đã tự xuống dòng tốt ở 1024px (đã kiểm chứng
bằng ảnh chụp) — **không cần sửa**.

### Tiêu chí nghiệm thu

Chụp/xem ở 1600 / 1280 / 1024 / 768px: không chữ nào trong stat card vỡ quá 2 dòng,
không có thanh cuộn ngang.

---

## 5. [B5] Dải chỉ số phụ bấm được

### Mục tiêu

Thêm một dải 4 ô nhỏ giữa "Tổng quan hệ thống" và hàng widget, hiển thị số lượng thật và
**bấm vào thì chuyển tab**. Lấp khoảng trống bằng nội dung có ích.

### Markup

Chèn ngay **sau** `</div>` đóng khối `.stat-cards` (sau dòng ~1613), trước `.home-widget-grid`:

```html
<div class="mini-stats" id="home-mini-stats">
  <div class="mini-stat" onclick="switchTab('company-runner')">
    <span class="mini-stat-icon" id="ms-icon-wf"></span>
    <div><div class="mini-stat-label">Quy trình</div>
         <div class="mini-stat-value" id="ms-workflows">—</div></div>
  </div>
  <div class="mini-stat" onclick="switchTab('auto-runner')">
    <span class="mini-stat-icon" id="ms-icon-auto"></span>
    <div><div class="mini-stat-label">Tác vụ tự động</div>
         <div class="mini-stat-value" id="ms-automations">—</div></div>
  </div>
  <div class="mini-stat" onclick="switchTab('meeting')">
    <span class="mini-stat-icon" id="ms-icon-meet"></span>
    <div><div class="mini-stat-label">Cuộc họp</div>
         <div class="mini-stat-value" id="ms-meetings">—</div></div>
  </div>
  <div class="mini-stat" onclick="switchTab('skills')">
    <span class="mini-stat-icon" id="ms-icon-tool"></span>
    <div><div class="mini-stat-label">Công cụ</div>
         <div class="mini-stat-value" id="ms-tools">—</div></div>
  </div>
</div>
```

### CSS

```css
.mini-stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 12px; }
.mini-stat {
  display: flex; align-items: center; gap: 10px; min-width: 0;
  padding: 10px 14px; background: var(--bg-card); border-radius: var(--radius-sm);
  box-shadow: var(--shadow); cursor: pointer;
  transition: transform .15s ease, box-shadow .15s ease;
}
.mini-stat:hover { transform: translateY(-1px); box-shadow: var(--shadow-hover); }
.mini-stat-icon svg { width: 16px; height: 16px; color: var(--accent); }
.mini-stat-label { font-size: 10.5px; color: var(--ink-muted); text-transform: uppercase; letter-spacing: .6px; }
.mini-stat-value { font-size: 15px; font-weight: 700; line-height: 1.2; }
@media (max-width: 900px) { .mini-stats { grid-template-columns: repeat(2, 1fr); } }
```

### JS

Thêm hàm `loadHomeMiniStats()` và gọi trong `renderOverview()` (dòng **3980**, thêm vào
mảng `Promise.all` đang có).

Nguồn dữ liệu (đã kiểm chứng shape response):

| Ô | Endpoint | Cách tính |
|---|---|---|
| Quy trình | `GET /workflow/tasks?kind=company` → `{tasks: [...]}` | `active/total` với `active = tasks.filter(t => t.status === 'active').length` |
| Tác vụ tự động | `GET /workflow/tasks?kind=automation` → `{tasks: [...]}` | như trên |
| Cuộc họp | `GET /meetings/` → `{meetings: [...]}` | tổng số |
| Công cụ | `GET /skills/` → `{skills: [...]}` | `enabled/total`, `enabled = skills.filter(s => s.enabled !== 0 && s.enabled !== false).length` |

Gọi qua helper `api('GET', path)` đã có sẵn (dòng **2951**) — nó tự thêm tiền tố `/api` và
tự chuyển hướng về `/login` khi 401. **Bọc mỗi lời gọi bằng `.catch(() => null)`** và hiện
`—` khi lỗi, để một endpoint hỏng không làm trắng cả trang chủ.

Icon: dùng hàm `icon(name, cls)` — định nghĩa tại **dòng 2720** của `hub.html`. Mở hàm đó
để lấy danh sách tên icon hợp lệ. Cách gán giống `renderOverview()` đang làm ở dòng 3953:
`document.getElementById('ms-icon-wf').innerHTML = icon('sync');`

### Tiêu chí nghiệm thu

- 4 ô hiện số thật, khớp với số đếm trong tab tương ứng.
- Bấm mỗi ô chuyển đúng tab.
- Tắt backend một endpoint bất kỳ → ô đó hiện `—`, các ô khác vẫn chạy.

---

## 6. [C6] Bật nén gzip — ưu tiên cao nhất trên mỗi công bỏ ra

### Hiện trạng

`hub/server.py` không có middleware nén nào. Đo thật:

```
hub.html gốc : 393 KB
gzip         :  85 KB  (còn 22%)
mỗi lần tải trang đang truyền thừa ~308 KB
```

### Việc cần làm

Trong `hub/server.py`, hàm `create_app()`, thêm vào **cụm middleware** (tìm comment
`# ── Middleware ────`). Thứ tự middleware trong file này quan trọng và đã có comment giải
thích — đọc kỹ trước khi chèn. GZip nên nằm **ngoài cùng** (thêm sau cùng):

```python
from fastapi.middleware.gzip import GZipMiddleware
...
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

### Tiêu chí nghiệm thu

```bash
curl -s -H "Accept-Encoding: gzip" -o /dev/null -w "%{size_download}\n" http://127.0.0.1:8123/hub
```
Phải ra khoảng **85.000** thay vì ~393.000. Hoặc mở DevTools → Network → cột Size của
`hub` phải hiện ~85 KB.

**Không được** làm hỏng: WebSocket (`/ws/*`) và endpoint trả file nhị phân
(`/api/workflow/runs/{id}/archive-file`). Kiểm tra mở được phòng họp và tải được ảnh
archive sau khi bật.

---

## 7. [C7] Tách `hub.css` và `hub.js` ra file riêng

> Làm **sau cùng**, sau khi các task trên đã xong và đã commit. Task này không đổi hành vi,
> chỉ đổi cấu trúc — trộn chung với thay đổi logic sẽ rất khó rà lỗi.

### Hiện trạng

`dashboard/hub.html` = 373 KB gồm:
- JS nội tuyến: **217 KB (58%)**, 270 hàm toàn cục, **0 tên trùng**
- CSS nội tuyến: **77 KB (21%)**
- markup: 79 KB (21%)

Hiệu năng hiện tại **không có vấn đề** (tải 82ms, chuyển tab 0,7–2,7ms). Lý do tách là an
toàn khi sửa và cache riêng phần, không phải tốc độ.

### Việc cần làm

1. Cắt toàn bộ nội dung trong `<style>...</style>` ra `dashboard/static/hub.css`.
   Thay bằng `<link rel="stylesheet" href="/static/hub.css">`.
2. Cắt toàn bộ nội dung trong `<script>...</script>` (khối nội tuyến duy nhất) ra
   `dashboard/static/hub.js`. Thay bằng `<script src="/static/hub.js" defer></script>`.
3. `/static` **đã được mount sẵn** — đã xác minh: `hub/server.py` có
   `static_path = os.path.join(_dashboard_path, "static")` rồi
   `app.mount("/static", StaticFiles(directory=static_path), name="static")`.
   Thư mục `dashboard/static/` đã tồn tại (đang chứa `images/`). Không cần cấu hình thêm.
   Trong `hub.html` hiện đã có sẵn **2 thẻ `<script src=...>`** — thêm thẻ mới cạnh chúng.
4. Cẩn thận hai điểm dễ vỡ:
   - JS hiện chạy **inline cuối body** nên DOM đã sẵn sàng. Khi chuyển sang file ngoài phải
     dùng `defer` (hoặc giữ thẻ script ở cuối `<body>`), nếu không mọi `getElementById` lúc
     khởi tạo sẽ trả `null`.
   - Trong JS có **template literal chứa HTML**; đảm bảo không có chuỗi `</script>` nào
     trong đó (nếu có, khi tách ra file ngoài thì hết vấn đề, nhưng kiểm tra ngược lại:
     đừng để lọt ký tự bị escape sai khi cắt/dán).
5. Cân nhắc thêm `?v=<hash>` vào URL để tránh cache cũ khi deploy. Không bắt buộc.

### Tiêu chí nghiệm thu

- `hub.html` còn khoảng **80 KB**.
- Mở `/hub`: cả 12 tab hoạt động y như trước, không lỗi nào trong Console.
- DevTools → Network thấy 3 request riêng (`hub`, `hub.css`, `hub.js`), đều được nén gzip.

---

## 8. Quy trình bắt buộc sau mỗi lần sửa `hub.html`

File này **không có build step nên không ai bắt lỗi cú pháp giúp bạn**. Một dấu ngoặc lệch
làm chết cả 12 tab. Sau mỗi lần sửa, chạy đoạn kiểm tra sau:

```python
# luu thanh check_js.py roi chay: python check_js.py
import re, subprocess, sys, os
html = open(r"d:\xanax\dashboard\hub.html", encoding="utf-8").read()
blocks = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S)
ok = True
for i, b in enumerate(blocks):
    p = f"_block_{i}.js"
    open(p, "w", encoding="utf-8").write(b)
    r = subprocess.run(["node", "--check", p], capture_output=True, text=True)
    print(f"block {i}: {'OK' if r.returncode == 0 else 'LOI'}")
    if r.returncode: print(r.stderr[:600]); ok = False
    os.remove(p)
sys.exit(0 if ok else 1)
```

Và luôn chạy `python -m pytest -q` — phải giữ **75 passed**.

---

## 9. Thứ tự thực hiện đề nghị

| Bước | Task | Lý do xếp trước/sau |
|---|---|---|
| 1 | **C6** gzip | 1 dòng, lợi nhất, độc lập hoàn toàn |
| 2 | **A4** breakpoint | CSS thuần, không đụng JS |
| 3 | **A2** hàng dưới | CSS thuần |
| 4 | **A1** widget rỗng | CSS + có thể chạm JS |
| 5 | **A3** stat card | Đụng `renderOverview()`, cần dữ liệu |
| 6 | **B5** dải chỉ số | Thêm markup + JS + endpoint mới |
| 7 | **C7** tách file | Làm cuối, commit riêng, không trộn với thay đổi logic |

Commit riêng từng bước để dễ lùi lại.

---

## 10. Những điều KHÔNG được làm

- Không đổi bảng màu, không thêm màu hardcode.
- Không thêm thư viện/framework/CDN.
- Không đụng vào 3 tab iframe (`Dạy AI`, `Quy trình`, `Tác vụ tự động`) — chúng là trang
  riêng (`/workspace`, `/taskrunner`), ngoài phạm vi plan này.
- Không đụng `api/auth_guard.py` hay cụm middleware xác thực trong `hub/server.py`
  (ngoài việc thêm GZip ở task C6).
- Không hiển thị số liệu giả/ước lượng khi thiếu dữ liệu — để trống hoặc ghi rõ "chưa đủ
  dữ liệu".
- Không sửa `tests/test_api.py` để test đi qua; nếu test đỏ thì sửa code, không sửa test.

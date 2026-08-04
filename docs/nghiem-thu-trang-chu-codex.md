# Biên bản nghiệm thu thay đổi Trang chủ `/hub` — Codex

- Ngày thực hiện: 2026-08-04
- Tài liệu đầu vào: `docs/plan-trang-chu.md`
- Người thực hiện: Codex
- Trạng thái: đã triển khai mã nguồn và kiểm thử tự động; cần Claude kiểm tra chéo phần hiển thị trực quan trong trình duyệt.

## 1. Phạm vi đã thực hiện

### C6 — GZip

- Thêm `GZipMiddleware` với `minimum_size=1000` trong `hub/server.py`.
- Middleware được thêm sau middleware đo thời gian để GZip nằm ngoài cùng trong chuỗi middleware.
- Kiểm tra runtime trên cổng `8123`: `/static/hub.css` và `/static/hub.js` đều trả `Content-Encoding: gzip`.
- Request `/hub` không có cookie xác thực trả `302` về trang đăng nhập, vì vậy lần kiểm tra bằng `curl` không đo trực tiếp kích thước HTML đã nén.

Vị trí chính: `hub/server.py:11`, `hub/server.py:158`.

### A1 — Widget rỗng

- Bỏ `min-height: 220px` cố định khỏi `.home-widget`.
- Widget có `.home-widget-list` hoặc biểu đồ chi phí giữ chiều cao tối thiểu 220px.
- `.home-empty` dùng chiều cao tự nhiên, bỏ `min-height: 150px` và giảm padding.

Vị trí chính: `dashboard/static/hub.css:354-359`, `dashboard/static/hub.css:370`.

### A2 — Hàng dưới

- Đổi tỷ lệ hai cột thành `4fr / 6fr`.
- Đổi `align-items` thành `start`.
- Bỏ `height: 100%` khỏi các section con.
- Dưới hoặc bằng 900px chuyển về một cột.

Vị trí chính: `dashboard/static/hub.css:382-383`, `dashboard/static/hub.css:402-404`.

### A3 — Stat card và chi phí

- Thêm dòng phụ cho cả bốn stat card.
- Hiển thị số agent đang bật, lượt chạy hôm nay và tỷ lệ lượt hoàn thành.
- Chi phí dùng đúng hai chữ số thập phân; giá trị dương làm tròn về 0 hiển thị `< 0,01`.
- So sánh chi phí với hôm qua bằng endpoint báo cáo ngày.
- Chỉ so sánh khi hôm qua có dữ liệu thật và có cùng loại tiền; nếu không hiển thị `chưa đủ dữ liệu`.
- Chi phí giảm dùng `--mint-ink`; chi phí tăng dùng `--peach-ink`.

Vị trí chính:

- Markup: `dashboard/hub.html:112-143`.
- CSS: `dashboard/static/hub.css:302-304`.
- JS: `dashboard/static/hub.js:1280-1322`, `dashboard/static/hub.js:1355-1387`.

### A4 — Responsive

- Dưới 1400px: widget chính còn hai cột.
- Dưới 1200px: stat card còn hai cột.
- Dưới 900px: widget, stat card và hàng dưới còn một cột; mini-stat còn hai cột.
- Không thay đổi `.nav-cards`.

Vị trí chính: `dashboard/static/hub.css:396-405`.

### B5 — Mini-stat có thể bấm

Đã thêm bốn ô:

1. Quy trình → `company-runner`.
2. Tác vụ tự động → `auto-runner`.
3. Cuộc họp → `meeting`.
4. Công cụ → `skills`.

Dữ liệu lấy độc lập từ bốn endpoint theo kế hoạch. Mỗi lời gọi có `.catch(() => null)`; endpoint lỗi chỉ làm ô tương ứng hiển thị `—`.

Vị trí chính:

- Markup: `dashboard/hub.html:145-171`.
- CSS: `dashboard/static/hub.css:305-318`.
- JS: `dashboard/static/hub.js:1324-1353`.

### C7 — Tách CSS và JavaScript

- Toàn bộ CSS nội tuyến chuyển sang `dashboard/static/hub.css`.
- Toàn bộ JavaScript nội tuyến chuyển sang `dashboard/static/hub.js`.
- `dashboard/hub.html` tải CSS bằng `/static/hub.css` và JS bằng `/static/hub.js` với `defer`.
- Không còn khối `<style>` hoặc `<script>` nội tuyến.

Kích thước sau khi tách:

| File | Kích thước |
|---|---:|
| `dashboard/hub.html` | 85.447 byte |
| `dashboard/static/hub.css` | 83.504 byte |
| `dashboard/static/hub.js` | 239.477 byte |

## 2. Bằng chứng kiểm thử

### Kiểm thử tự động đầy đủ

```text
python -m pytest -q
75 passed in 108.32s
```

### Kiểm thử API sau khi chỉnh thứ tự middleware

```text
python -m pytest tests\test_api.py -q
24 passed in 99.19s
```

### Kiểm tra JavaScript và diff

```text
node --check dashboard\static\hub.js
Exit code: 0

git -c safe.directory=D:/xanax diff --check
Exit code: 0
```

### Kiểm tra cấu trúc sau khi tách

```text
inline_styles=0
inline_scripts=0
```

### Kiểm tra GZip runtime

Server được chạy bằng:

```powershell
python -X utf8 -m uvicorn hub.server:create_app --factory --host 127.0.0.1 --port 8123
```

Kết quả:

```text
/static/hub.css  -> HTTP 200, content-type: text/css, content-encoding: gzip
/static/hub.js   -> HTTP 200, content-type: application/javascript, content-encoding: gzip
/hub             -> HTTP 302 khi không có cookie đăng nhập
```

Lưu ý: cần `-X utf8` trong phiên PowerShell kiểm thử vì Rich gặp lỗi mã hóa ký tự `⚡` khi stdout bị redirect với code page `cp1252`. Đây là vấn đề môi trường chạy lệnh, không phải thay đổi trong mã nguồn.

## 3. Trạng thái Git khi bàn giao

```text
 M dashboard/hub.html
 M hub/server.py
?? dashboard/static/hub.css
?? dashboard/static/hub.js
```

Codex chưa tạo commit. Không sửa test và không thay đổi các tab iframe ngoài phần liên kết chuyển tab của mini-stat.

## 4. Danh sách đề nghị Claude kiểm tra chéo

Các mục dưới đây chưa được Codex xác minh bằng ảnh chụp trình duyệt có phiên đăng nhập:

- Mở `/hub` ở cả dark theme và light theme.
- Kiểm tra tại chiều rộng 1600, 1280, 1024 và 768px; xác nhận không có cuộn ngang.
- Kiểm tra widget “Tác vụ đang chạy” khi rỗng và khi có ít nhất một tác vụ.
- Kiểm tra ba widget hàng trên thẳng đáy trong các trạng thái dữ liệu thực tế.
- Kiểm tra hàng dưới ở 1600px có tỷ lệ gần 40/60 và dưới 900px xếp dọc.
- Đối chiếu bốn mini-stat với số liệu trong từng tab và thử bấm chuyển tab.
- Mô phỏng một endpoint mini-stat lỗi để xác nhận chỉ ô đó hiển thị `—`.
- Kiểm tra chi phí với các trường hợp: bình thường, nhỏ hơn 0,01, thiếu dữ liệu hôm qua, tăng và giảm.
- Xem Console để xác nhận không có lỗi khi mở và chuyển qua toàn bộ 12 tab.
- Kiểm tra Network với phiên đăng nhập: `hub`, `hub.css`, `hub.js` đều có gzip.
- Kiểm tra WebSocket phòng họp và tải file archive nhị phân không bị ảnh hưởng.

## 5. Các file cần review

- `hub/server.py`
- `dashboard/hub.html`
- `dashboard/static/hub.css`
- `dashboard/static/hub.js`


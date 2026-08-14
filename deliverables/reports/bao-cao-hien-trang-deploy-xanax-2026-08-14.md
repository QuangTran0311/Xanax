# Báo cáo hiện trạng và mức sẵn sàng triển khai Xanax

**Ngày đánh giá:** 14/08/2026  
**Phạm vi:** mã nguồn tại `D:\xanax`  
**Nhánh:** `main`  
**Revision:** `e17fe0f`  
**Phiên bản ứng dụng:** `2.2.0`

## 1. Kết luận điều hành

Xanax đã đủ chức năng để chạy thử nghiệm trên một máy chủ riêng, nhưng **chưa nên mở trực tiếp ra Internet với cấu hình hiện tại**. Mức sẵn sàng được đánh giá khoảng **5/10**.

Ứng dụng có frontend production, lớp xác thực chung cho API và WebSocket, health endpoint, mã hóa bí mật lưu trong database và bộ test tương đối lớn. Các rào cản chính không nằm ở khả năng xử lý AI mà ở cấu hình production, HTTPS, quản lý secret, tính tương thích môi trường máy chủ và quy trình sao lưu/khôi phục.

Sau khi hoàn thành các mục P0 trong báo cáo này, project phù hợp để triển khai thử cho cá nhân hoặc nhóm nhỏ trên một VPS phổ thông, không cần GPU.

## 2. Kiến trúc hiện tại

| Thành phần | Công nghệ/hiện trạng |
|---|---|
| Backend | Python 3.11, FastAPI, Uvicorn |
| Frontend | React 19, TypeScript, Vite |
| Kết nối thời gian thực | WebSocket |
| Database | SQLite qua `aiosqlite` |
| Lập lịch | APScheduler và hàng đợi tác vụ nội bộ |
| Model AI | Model/API/CLI bên ngoài; server không huấn luyện model |
| Lưu trữ file | `backend/data` trên filesystem cục bộ |
| Phục vụ frontend | Backend phục vụ bản build trong `frontend/dist` |
| Reverse proxy/TLS | Chưa có cấu hình trong repo |
| Container | Chưa có Dockerfile hoặc Compose |
| CI/CD | Chưa có workflow CI trong repo |

## 3. Kết quả kiểm tra kỹ thuật

### 3.1. Frontend

- `npm run build`: **PASS**.
- `npm run verify:graphs`: **PASS**.
- `npm run verify:workflow-protocol`: **PASS**.
- `npm run verify:meeting-protocol`: **PASS**.
- `npm run verify:hub-integration`: **PASS**.
- Kích thước `frontend/dist` tại thời điểm đo: khoảng **3,73 MiB**.

### 3.2. Backend

- Tổng kết lần chạy test trên bản sao cô lập: **316 test pass, 1 test fail**.
- Test còn lỗi: `TestAuthGuard.test_webhook_stays_public`.
- Triệu chứng: database test sạch chưa có bảng `workflow_tasks`.
- Đánh giá ban đầu: nhiều khả năng fixture test chưa gọi đầy đủ `init_db`; chưa phải bằng chứng rằng webhook trên database production đã hỏng. Tuy nhiên release gate vẫn phải đạt 100% trước khi phát hành.

### 3.3. Trạng thái mã nguồn

- Repo có **183 file đang được Git theo dõi**.
- Worktree hiện có khoảng **50 mục thay đổi/chưa theo dõi**.
- Đây không mặc nhiên là lỗi, nhưng cần đóng băng một revision triển khai rõ ràng để có thể rollback và tái tạo server.
- Quét mẫu secret trong các file đang được Git theo dõi không phát hiện private key hoặc API key dạng phổ biến. Kết quả này không thay thế công cụ secret scanning chuyên dụng.

### 3.4. Dung lượng dữ liệu hiện tại

| Hạng mục | Dung lượng xấp xỉ |
|---|---:|
| `backend/xanax.db` | 1,64 MiB |
| `backend/data` | 211,28 MiB |
| `frontend/dist` | 3,73 MiB |

Ổ 60 GB đủ cho giai đoạn đầu. Thư mục cần theo dõi tăng trưởng nhiều nhất là `backend/data`, đặc biệt khi workflow tạo ảnh và lưu kết quả thường xuyên.

## 4. Điểm đã đáp ứng tốt

- Có middleware xác thực tập trung, mặc định bảo vệ `/api/*` và `/ws/*`.
- WebSocket có xử lý trường hợp phiên đăng nhập hết hạn.
- Mật khẩu được băm bằng PBKDF2 với salt riêng.
- API key/token của skill có cơ chế mã hóa khi lưu.
- `.env`, database và thư mục dữ liệu đã được loại khỏi Git bằng `.gitignore`.
- Có health endpoint công khai cho reverse proxy hoặc uptime monitor.
- Frontend và backend cùng origin, thuận lợi cho cookie, WebSocket và reverse proxy.
- Có gzip response và frontend build tĩnh.
- Có cơ chế khôi phục một số lịch chạy và trạng thái bị gián đoạn sau restart.

## 5. Rủi ro và việc cần hoàn thành

### P0 — bắt buộc trước khi public Internet

1. **Thay toàn bộ secret production**
   - `HUB_SECRET_KEY` và `HUB_API_KEY` hiện vẫn tương ứng cấu hình placeholder/dev.
   - Phải đặt `XANAX_SECRET_KEY` cố định và sao lưu an toàn.
   - Không ghi giá trị secret vào Git hoặc tài liệu triển khai.

2. **Tắt chế độ debug**
   - Đặt `HUB_DEBUG=false`.
   - Debug hiện làm Uvicorn reload và mở CORS rộng.

3. **Không sử dụng tài khoản mặc định**
   - Server có thể tạo `admin/xanax` khi database chưa có user.
   - Phải đặt `XANAX_ADMIN_USER` và mật khẩu mạnh trước lần khởi động đầu tiên trên server.

4. **Bật HTTPS và cookie an toàn**
   - Cookie phiên hiện đặt `secure=False`.
   - Cần reverse proxy có TLS và sửa cookie thành `Secure` khi chạy production.
   - Chỉ public cổng 80/443; cổng backend chỉ nghe loopback.

5. **Thêm rate limiting đăng nhập**
   - `/api/auth/login` chưa có lớp hạn chế brute-force rõ ràng.

6. **Đóng gói một revision triển khai**
   - Commit hoặc tạo release từ trạng thái đã kiểm thử.
   - Không triển khai trực tiếp một worktree có nhiều thay đổi chưa được định danh.

7. **Làm xanh toàn bộ test**
   - Sửa fixture/schema của test webhook và yêu cầu 317/317 test pass.

### P1 — cần hoàn thành cho vận hành ổn định

1. **Tạo cấu hình triển khai có thể tái lập**
   - Có thể dùng Windows service + Caddy cho giai đoạn đầu.
   - Lưu tài liệu cài Python, Node build, biến môi trường, service và firewall.

2. **Chuẩn hóa dependency**
   - `requirements.txt` có `Pillow`, `mcp`, `cryptography` nhưng `pyproject.toml` chưa có các dependency này.
   - Cần chọn một nguồn dependency chính để tránh build bằng `pyproject.toml` nhưng thiếu package lúc runtime.

3. **Cải thiện readiness probe**
   - `/api/health/ready` hiện luôn trả `ready=true`.
   - Nên kiểm tra tối thiểu database và trạng thái các dịch vụ nội bộ bắt buộc.

4. **Thiết kế backup/restore độc lập nhà cung cấp**
   - Backup `xanax.db`, toàn bộ `backend/data`, `.env` và khóa mã hóa.
   - Thử restore định kỳ; backup chưa từng restore chưa được xem là đảm bảo.

5. **Giám sát tài nguyên**
   - Theo dõi RAM, CPU, dung lượng ổ, lỗi 5xx, restart service và độ trễ API model.

6. **Giữ một process ứng dụng**
   - SQLite, scheduler và hàng đợi nội bộ chưa phù hợp scale ngang/multiple Uvicorn workers.
   - Giai đoạn đầu chỉ chạy một process Xanax.

### P2 — cải tiến sau khi hệ thống ổn định

- Chuyển PostgreSQL nếu cần nhiều người dùng hoặc nhiều process đồng thời.
- Tách object storage nếu ảnh và archive tăng nhanh.
- Bổ sung CI/CD, secret scanning và kiểm thử restore tự động.
- Cải thiện tính di động Linux; hiện vẫn còn một số đường dẫn/fallback thiên về Windows.
- Ẩn hoặc giới hạn API docs trên production nếu không cần công khai.

## 6. Cấu hình production tối thiểu đề xuất

```dotenv
HUB_HOST=127.0.0.1
HUB_PORT=8000
HUB_DEBUG=false
HUB_TASK_WORKER_COUNT=2
XANAX_NO_BROWSER=1

# Các giá trị dưới đây phải là secret thật và không đưa vào Git:
HUB_SECRET_KEY=<random-secret>
HUB_API_KEY=<random-api-key>
XANAX_SECRET_KEY=<stable-encryption-key>
XANAX_ADMIN_USER=<admin-name>
XANAX_ADMIN_PASS=<strong-password>
```

Lưu ý: `XANAX_SECRET_KEY` phải được giữ ổn định. Mất hoặc thay khóa này có thể khiến các token đã mã hóa trong database không còn giải mã được.

## 7. Release gate đề xuất

Chỉ public hệ thống khi tất cả điều kiện sau đạt:

- [ ] Frontend build và bốn script verify đều pass.
- [ ] Backend test pass 100%.
- [ ] Có revision Git/tag dùng để triển khai và rollback.
- [ ] Debug đã tắt; secret và tài khoản mặc định đã được thay.
- [ ] HTTPS hoạt động; cookie phiên có cờ `Secure`.
- [ ] Cổng backend không public trực tiếp.
- [ ] Đăng nhập có rate limit.
- [ ] WebSocket hoạt động qua HTTPS (`wss://`).
- [ ] Restart server không làm hỏng lịch chạy hoặc dữ liệu.
- [ ] Backup ngoài VPS đã chạy thành công.
- [ ] Restore thử nghiệm đã thành công.
- [ ] Theo dõi CPU/RAM/disk và cảnh báo dung lượng đã được thiết lập.

## 8. Đánh giá cuối cùng

| Phạm vi sử dụng | Đánh giá |
|---|---|
| Chạy local | Đạt |
| Staging/private server | Có thể triển khai sau khi đặt secret |
| Public Internet hiện tại | Chưa đạt |
| Public Internet sau khi hoàn thành P0 | Phù hợp cho cá nhân/nhóm nhỏ |
| Nhiều người dùng/scale ngang | Chưa phù hợp; cần thay đổi database và kiến trúc worker |


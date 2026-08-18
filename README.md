# Xanax — AI Agent ERP

Xanax là hệ thống quản lý **nhân viên AI như một công ty**: tuyển (tạo agent), giao việc, xếp thành quy trình nhiều bước, họp bàn, nghiệm thu kết quả, và theo dõi chi phí token.

Chạy hoàn toàn trên máy cá nhân (Windows). Hai nửa tách bạch:

| | Thư mục | Công nghệ |
|---|---|---|
| **Backend** | `backend/` | FastAPI + SQLite + WebSocket |
| **Frontend** | `frontend/` | React + TypeScript + Vite (SPA) |

Khi chạy thật, **FastAPI phục vụ cả API, WebSocket và bản build frontend trên cùng một cổng** — một origin duy nhất, cookie đăng nhập không phải đi cross-origin, không cần CORS.

---

# Chạy dự án

## 1. Cần có sẵn trên máy

| | Kiểm bằng | Ghi chú |
|---|---|---|
| Python 3.11+ | `python --version` | |
| Node.js 20+ | `node -v` | Chỉ cần khi **build** hoặc **sửa** frontend |
| npm | `npm -v` | Đi kèm Node |

Frontend chỉ cần Node lúc build. Sau khi đã có `frontend/dist/`, chạy hằng ngày **chỉ cần Python**.

## 2. Cài lần đầu

### Bước 1 — Python

Máy này hiện **không có venv riêng trong dự án**. Xanax đang chạy chung venv với Hermes:

```
C:\Users\Quang\AppData\Local\hermes\hermes-agent\venv
```

Đó là chủ ý: Xanax đọc/ghi `SOUL.md` của Hermes và dùng chung một số phụ thuộc. Cứ giữ nguyên thì không phải cài gì thêm.

Nếu muốn một venv riêng cho dự án:

```powershell
cd D:\xanax\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

> Lưu ý: venv riêng sẽ **không có `playwright`**, nên `scripts/smoke_hub.py` không chạy được cho tới khi `pip install playwright` và `playwright install chromium`.

### Bước 2 — File cấu hình

```powershell
cd D:\xanax\backend
copy .env.example .env
```

Mở `backend\.env` và đặt ba giá trị trước khi dùng thật:

| Biến | Ý nghĩa |
|---|---|
| `HUB_SECRET_KEY` | Khoá ký của server. Đang là chuỗi placeholder |
| `HUB_API_KEY` | Khoá cho đường `X-API-Key`. Đang là placeholder |
| `XANAX_SECRET_KEY` | Khoá AES mã hoá `api_key`/`token` của skill |

Sinh một khoá 32 byte:

```powershell
python -c "import base64,os;print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

> **⚠ Đừng đổi `XANAX_SECRET_KEY` khi đã có skill lưu token.** Mọi bí mật đã lưu đều mã hoá bằng khoá cũ; đổi khoá là **không giải mã lại được và không có đường khôi phục** — phải nhập tay lại toàn bộ. Khoá hiện dùng nằm ở `backend/.env` và `backend/data/.secret_key`, hai chỗ phải khớp nhau.

### Bước 3 — Build frontend

```powershell
cd D:\xanax\frontend
npm install
npm run build
```

Sinh ra `frontend/dist/`. Backend tự tìm thấy thư mục này.

## 3. Chạy hằng ngày

```powershell
cd D:\xanax\backend
python main.py
```

Trình duyệt tự mở tới `http://localhost:8000`. Tắt tự mở bằng `set XANAX_NO_BROWSER=1`.

| Địa chỉ | |
|---|---|
| `http://localhost:8000` | Giao diện — vào là ra trang đăng nhập |
| `http://localhost:8000/api/docs` | Tài liệu API tự sinh |
| `http://localhost:8000/api/health` | Kiểm tra server sống |
| `http://localhost:8000/api/version` | Phiên bản đang chạy — công khai chỉ trả `version`; `commit` chỉ trả khi đã xác thực |

**Đăng nhập lần đầu:** chưa có user nào thì lúc khởi động server tự tạo `admin` / `xanax` và in ra màn hình. Đổi bằng `XANAX_ADMIN_USER` / `XANAX_ADMIN_PASS` trong `.env`.

> Mọi phiên đăng nhập **bị xoá mỗi lần restart server**. Đăng nhập lại là bình thường, không phải lỗi.

Dừng server: `Ctrl+C`.

## 4. Chạy khi đang sửa giao diện

Chỉ cần khi sửa code trong `frontend/src`. Mở **hai** cửa sổ PowerShell:

```powershell
# Cửa sổ 1 — backend
cd D:\xanax\backend
python main.py
```

```powershell
# Cửa sổ 2 — frontend, tự nạp lại khi lưu file
cd D:\xanax\frontend
npm run dev
```

Mở `http://localhost:5173`. Vite proxy `/api` và `/ws` sang cổng 8000, nên cookie vẫn là same-origin và **không cần bật CORS**.

> Nếu gặp 401 khắp nơi lúc dev thì lỗi ở proxy trong `frontend/vite.config.ts`, **không phải** ở cookie. Đừng "sửa" bằng cách mở CORS hay đổi `SameSite`.

Sửa xong: `npm run build` rồi quay lại cách chạy ở mục 3.

## 5. Chạy cái gì khi nào

| Bạn vừa làm gì | Cần chạy |
|---|---|
| Sửa Python trong `backend/` | Không gì cả — `HUB_DEBUG=true` nên uvicorn tự reload |
| Sửa React trong `frontend/src` | `npm run dev` lúc làm, `npm run build` khi xong |
| Kéo code mới về | `pip install -r requirements.txt` và `npm install`, rồi `npm run build` |
| Chỉ muốn dùng, không sửa gì | `python main.py` |

## 6. Lệnh hay dùng

**Backend** (`cd D:\xanax\backend`)

```powershell
python main.py                            # chạy server
python -m pytest tests/ -q                # 334 test
python scripts\smoke_hub.py               # Playwright: đi hết 12 tab trên trình duyệt thật
python tools\migrate_mcp_server_paths.py  # xem trước; thêm --apply để ghi
```

**Frontend** (`cd D:\xanax\frontend`)

```powershell
npm run dev                       # dev server cổng 5173
npm run build                     # build ra dist/
npm run typecheck                 # kiểm kiểu, không sinh file
npm run verify:graphs             # graph_json thật giữ nguyên từng byte
npm run verify:workflow-protocol  # phủ đủ message type của /ws/workflow
npm run verify:meeting-protocol   # reducer phòng họp
npm run verify:hub-integration    # không còn iframe, tab giữ state, route nặng lazy
```

Bốn script `verify:*` đọc **DB thật** và **mã backend thật** rồi đối chiếu — chúng bắt được lỗi lệch hợp đồng giữa hai nửa mà typecheck không thấy.

## 7. Hỏng thì xem đây trước

| Triệu chứng | Xử lý |
|---|---|
| `ModuleNotFoundError: cryptography` | `pip install -r requirements.txt` — gói này bắt buộc, không gói nào kéo theo nó |
| Mở `localhost:8000` ra trang trắng | Chưa build frontend. `cd frontend && npm run build` |
| Cấu hình `.env` như không có tác dụng | Đang chạy sai thư mục? Phải `cd backend` rồi mới `python main.py` |
| Đăng nhập xong lại bị đá ra | Bình thường sau khi restart server — mọi phiên bị xoá |
| Cổng 8000 đã bị chiếm | `Get-NetTCPConnection -LocalPort 8000 -State Listen` để xem tiến trình nào |
| Sửa React mà giao diện không đổi | Đang mở cổng 8000 (bản build cũ) thay vì 5173 (bản dev) |

---

# Kiến trúc

```
Trình duyệt
    │
    │  cùng một origin — cookie xanax_session đi kèm mọi request
    ▼
┌─────────────────────────────────────────────┐
│  FastAPI  :8000                             │
│                                             │
│  /api/*   97 đường dẫn   ─┐                 │
│           135 operation   ├─ AuthGuard gác  │
│  /ws/*    7 kênh         ─┘                 │
│                          ─┘                 │
│  /*       SPA fallback → frontend/dist      │
└─────────────────────────────────────────────┘
```

SPA fallback trả `index.html` cho **mọi** đường dẫn không bắt đầu bằng `/api` hay `/ws`, để React Router tự định tuyến. Hai tiền tố đó được loại trừ tường minh — nếu không, API sẽ trả về HTML và cả hệ thống hỏng cùng lúc.

## Ý tưởng cốt lõi

| Khái niệm ERP | Trong Xanax | Bảng DB |
|---|---|---|
| Nhân viên | Agent — có persona, phòng ban, model riêng, file `soul.md` riêng | `agent_configs`, `departments` |
| Kỹ năng nghề | Skill — prompt, HTTP API, hoặc MCP server | `skills` |
| Quy trình | Workflow — chuỗi nhiều nhân viên nối tiếp nhau | `workflow_tasks` |
| Lượt làm việc | Run — mỗi lần chạy quy trình, có kết quả từng bước | `workflow_runs`, `workflow_outputs` |
| Đánh giá nhân sự | Papa duyệt ĐẠT/KHÔNG ĐẠT → ghi vào `soul.md` của nhân viên đó | `workflow_outputs.pass_fail` |
| Phòng họp | Nhiều agent + Xanax cùng thảo luận, có thể kích hoạt quy trình | `meetings` |
| Ngân sách | Model Pool + giới hạn request/token theo ngày + báo cáo chi phí | `model_pool`, `model_usage` |

**Xanax** (tên hệ thống, cũng là tên trợ lý điều phối) là agent cấp trên: đọc snapshot DB tươi mỗi tin nhắn, tự tạo công việc, kích hoạt quy trình, và ghi nhớ bài học vào `SOUL.md`.

## 12 tab trong `/hub`

| Tab | URL | Nội dung |
|---|---|---|
| Tổng quan | `/hub` | Thẻ thống kê, widget hoạt động, cảnh báo, biểu đồ chi phí |
| Nhân sự | `/hub/agents` | CRUD agent, gán model + kỹ năng + phòng ban, xem `soul.md` |
| Kỹ năng | `/hub/skills` | CRUD skill 3 loại: `custom` / `api` / `mcp` — có nút kiểm tra kết nối |
| Dự án | `/hub/tasks` | Kanban công việc, matcher gợi ý người phù hợp, cảnh báo không khớp |
| Họp | `/hub/meeting` | Phòng họp nhiều agent, realtime qua WebSocket |
| Dạy AI | `/hub/train` | Chat dạy quy tắc → lưu vào soul của học viên |
| Quy trình | `/hub/company-runner` | Thiết kế + chạy quy trình nhiều bước, duyệt từng output |
| Tác vụ tự động | `/hub/auto-runner` | Quy trình chạy theo lịch cron / webhook |
| Tài sản | `/hub/assets` | File upload + kết quả quy trình đã lưu trữ, tải về |
| Bộ não AI | `/hub/model` | 3 mục: Model Pool · Đánh giá model · Thí nghiệm tự cải thiện |
| Chi phí | `/hub/cost` | Thống kê token/chi phí, xuất báo cáo `.xlsx` |
| Cài đặt | `/hub/settings` | Giao diện, ngôn ngữ, thông tin phiên |

Ngoài `/hub` còn `/workspace` (dạy AI toàn màn hình) và `/taskrunner` (quy trình toàn màn hình). Ba màn hình này **dùng chung component React** với tab tương ứng trong Hub — không qua iframe, nên trạng thái tab được giữ khi chuyển qua lại.

Định tuyến nằm hoàn toàn ở client (`frontend/src/routes.tsx` và `HubPage.tsx`). Backend không còn danh sách tab nào.

---

## Hệ thống Skill — 3 loại

Skill là "kỹ năng nghề" gán cho nhân viên. Khi nhân viên chạy, mọi skill được gán sẽ thành **tool** mà model gọi được.

### 1. `custom` — prompt thuần
Nội dung file markdown trong `backend/skills/`, nhét vào system prompt. Không gọi ra ngoài.

### 2. `api` — HTTP endpoint
Khai báo method / URL / headers / body template. `core/skill_tools.py` sinh tool động, đăng ký vào `ToolRegistry`.

Có xử lý riêng cho Facebook Page: tự đổi sang `/photos` khi bài đăng kèm ảnh do quy trình vừa tạo.

### 3. `mcp` — Model Context Protocol
`core/mcp_client.py` là MCP client thật, hỗ trợ 3 transport: **stdio**, **http** (streamable), **sse**.

```
Skill "cat_anh_san_pham"  (type: mcp)
  ├─ transport: stdio
  ├─ target: <python.exe venv rembg> D:\xanax\backend\mcp_servers\image_cut.py
  └─ tools: ["cut_product", "cut_product_batch"]   ← chọn từng tool, không phải all-or-nothing
```

Chi tiết đáng lưu ý:
- **Một thẻ skill chứa nhiều tool.** UI hiện danh sách tool kèm checkbox; bỏ chọn tool nào thì tool đó không được đăng ký.
- **Đổi lựa chọn tool không cần kết nối lại** — chỉ đăng ký lại registry (0.01s thay vì ~7s).
- `tools: []` (bỏ chọn hết) khác với không có khoá `tools` (lấy tất cả). Đây là phân biệt cố ý.
- Kết nối được giữ bền bởi một supervisor task; `mcp_manager.close_all()` chạy khi server tắt.
- Tool trả về ảnh (`ImageContent`) được ghi ra `backend/data/mcp-images/YYYYMMDD/` và trả về đường dẫn file.
- Tiền tố tên tool do backend sinh (`core/slugify.py`, có bóc dấu tiếng Việt) và trả về qua `GET /api/tools/mcp/status` — **frontend không được tự slugify lại**.
- `target` trong DB là **đường dẫn tuyệt đối**. Dời thư mục dự án là skill chết lặng lẽ (MCP báo `pending`, tool biến mất). Sửa bằng `python tools/migrate_mcp_server_paths.py` — mặc định chỉ xem trước, `--apply` để backup DB rồi ghi.

### MCP server có sẵn: `backend/mcp_servers/image_cut.py`

Cắt ảnh sản phẩm: tách nền → cắt sát viền → chừa lề → đưa về tỉ lệ khung bài đăng.

```
cut_product(input_path, output_path, model="birefnet-general-lite",
            padding_percent=2.0, ratio="", background="transparent",
            alpha_matting=False, alpha_matting_foreground_threshold=240,
            alpha_matting_background_threshold=10, alpha_matting_erode_size=10)
cut_product_batch(...)
```

Chạy bằng Python của venv `rembg`, **không phải** venv xanax.

Model mặc định `birefnet-general-lite` — đo trên ảnh chụp thật, đây là model duy nhất xử lý sạch cả nền tối lẫn **bóng đổ trên mặt bàn**, và không làm bạc chi tiết tối của sản phẩm. Giá: 13,5s/ảnh và 214MB tải về. Cần nhanh thì `model="u2netp", alpha_matting=True` (~5s), chấp nhận bóng đổ còn sót.

Đừng nâng `erode_size` quá 10 và đừng dùng `isnet-general-use` — cả hai đều đã đo và đều làm hỏng ảnh. Toàn bộ số đo, cơ chế, và giới hạn: [docs/tach-nen-san-pham.md](docs/tach-nen-san-pham.md).

---

## Bảo mật

### Gác xác thực — `backend/api/auth_guard.py`

ASGI middleware thuần **mặc định ĐÓNG**: mọi `/api/*` và `/ws/*` đều yêu cầu phiên đăng nhập, trừ danh sách mở tường minh.

```python
_PUBLIC_EXACT   = {"/api/auth/login", "/api/auth/logout", "/api/auth/me",
                   "/api/health", "/api/health/ready", "/api/version"}
_OPTIONAL_AUTH_EXACT = {"/api/version"}  # có xác thực mới trả thêm commit
_PUBLIC_PREFIXES = ("/api/workflow/hooks/",)   # webhook có token riêng trong URL
_GUARDED_PREFIXES = ("/api/", "/ws/")
```

Ba lựa chọn thiết kế có chủ ý:

- **Middleware thay vì `Depends` từng router** — route mới thêm sau tự động được bảo vệ; kiểu `Depends` thì mỗi router mới là một cơ hội quên.
- **ASGI thuần thay vì `@app.middleware("http")`** — cái sau chỉ chạy với scope `http`, WebSocket sẽ lọt lưới, mà `/ws/meeting` chính là nơi chứa nội dung họp và quyền kích hoạt quy trình.
- **`websocket.accept()` trước khi đóng `1008`.** Dòng accept trông thừa nhưng không thừa: theo chuẩn ASGI, gửi `websocket.close` mà chưa accept là *từ chối bắt tay*, và uvicorn dịch nó thành **HTTP 403** — trình duyệt chỉ thấy handshake hỏng với mã 1006, không bao giờ nhận được 1008. Frontend dựa vào 1008 để phân biệt "hết phiên" (về trang đăng nhập, KHÔNG thử lại) với "mạng đứt" (nối lại).

**Thứ tự middleware trong `hub/server.py` là quan trọng:**

```python
app.add_middleware(AuthGuardMiddleware)   # thêm TRƯỚC → nằm trong
app.add_middleware(CORSMiddleware, ...)   # thêm SAU  → nằm ngoài
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

CORS phải nằm ngoài AuthGuard vì preflight `OPTIONS` không mang cookie — nếu ngược lại, mọi preflight sẽ bị chặn 401.

### Mã hoá bí mật khi lưu — `backend/core/secret_crypto.py`

AES-256-GCM cho các khoá nhạy cảm trong `skills.config_json`:

```
enc:v1:<base64(nonce || ciphertext)>
SECRET_CONFIG_KEYS = ("api_key", "token")
```

- Khoá lấy theo thứ tự: biến môi trường `XANAX_SECRET_KEY` → cùng khoá đó trong `backend/.env` → `backend/data/.secret_key` → tự sinh mới.
- API trả về giá trị đã che (`••••••••`); khi lưu, giá trị che được merge lại thành giá trị cũ — sửa mô tả skill không làm mất token.
- Đây là bảo vệ **dữ liệu khi nằm yên**, không phải bảo vệ quyền truy cập API. Ai qua được `auth_guard` vẫn dùng được skill.
- Di trú dữ liệu cũ: `python tools/encrypt_existing_secrets.py` (mặc định chỉ xem trước, `--apply` để ghi, tự backup DB và kiểm tra giải mã khớp).

> Mất `backend/data/.secret_key` **và** không ghim khoá trong `.env` là mất luôn mọi token đã lưu. File đó nằm trong `.gitignore`, git không giữ hộ.

### Phiên đăng nhập

TTL 8h (server) · cookie `xanax_session` HttpOnly, **SameSite=lax**, `max_age` 7 ngày · nhịp tim client 5 giây gọi `/api/auth/me` · purge cron 30 phút · mật khẩu PBKDF2-HMAC-SHA256 260.000 vòng · **mọi phiên bị xoá khi server restart**.

Cookie để `SameSite=lax` và `secure=False` được là nhờ frontend cùng origin với backend. Nếu tách sang origin khác thì phải đổi sang `SameSite=None; Secure` và bật HTTPS thật.

---

## Cấu trúc thư mục

```
xanax/
├── backend/
│   ├── main.py                      # uvicorn runner + banner + tự mở trình duyệt
│   ├── requirements.txt
│   ├── .env                         # cấu hình thật (không commit)
│   ├── xanax.db                     # SQLite, tự tạo — 30 bảng
│   │
│   ├── hub/
│   │   ├── server.py                # create_app(): route, middleware, lifespan,
│   │   │                            # mount dist/ và SPA fallback
│   │   ├── config.py                # Pydantic Settings (env prefix HUB_)
│   │   ├── database.py              # aiosqlite — toàn bộ DB + migration
│   │   └── events.py                # event bus nội bộ
│   │
│   ├── api/
│   │   ├── auth_guard.py            # gác xác thực /api/* và /ws/*
│   │   ├── websocket.py             # /ws/chat
│   │   ├── websocket_training.py    # /ws/training — live context + Xanax tool use
│   │   ├── websocket_workflow.py    # /ws/workflow — chạy quy trình nhiều bước
│   │   ├── websocket_meeting.py     # /ws/meeting — phòng họp nhiều agent
│   │   ├── websocket_benchmark.py   # /ws/benchmark
│   │   ├── websocket_task.py
│   │   ├── websocket_experiment.py  # /ws/experiments/{id} — chạy thí nghiệm ablation
│   │   ├── agents/
│   │   │   ├── subprocess_util.py   # subprocess an toàn trên Windows (BẮT BUỘC)
│   │   │   ├── claude_runner.py     # wrapper Claude CLI (stream-json)
│   │   │   └── codex_runner.py      # wrapper Codex CLI (prompt qua stdin)
│   │   └── routes/                  # 20 module, 97 đường dẫn · 135 operation
│   │
│   ├── core/
│   │   ├── mcp_client.py            # MCP client: stdio/http/sse, chọn tool, ảnh
│   │   ├── skill_tools.py           # skill type "api" → tool động
│   │   ├── secret_crypto.py         # AES-256-GCM cho api_key/token
│   │   ├── model_pool_bridge.py     # gọi model qua pool, LimitExceededError
│   │   ├── agent_prompt.py          # ghép prompt tri thức dùng chung cho agent
│   │   ├── experiment_runner.py     # chạy ablation ba tầng + chấm mù
│   │   ├── cli_provider.py          # gọi model qua CLI gói thuê bao,
│   │   │                            # build_clean_env() chặn rò rỉ sang gateway
│   │   ├── hermes_bridge.py         # LLM client + phiên chat in-memory
│   │   ├── image_gen.py             # sinh ảnh, ImageGenError với lỗi cụ thể
│   │   ├── image_compose.py         # ghép ảnh sản phẩm lên nền
│   │   ├── agent_soul.py            # soul.md riêng từng nhân viên
│   │   ├── project_soul.py          # soul riêng từng dự án
│   │   ├── skill_soul.py            # phụ lục bài học của skill
│   │   ├── soul_sync.py             # SOUL.md của Xanax
│   │   ├── project_storage.py       # archive kết quả run ra ổ đĩa
│   │   ├── rag.py                   # truy hồi tài liệu bằng keyword overlap
│   │   ├── matcher.py               # khớp nhân viên ↔ công việc
│   │   ├── orchestrator.py          # điều phối agent chạy ngầm
│   │   ├── scheduler.py             # APScheduler: cron / delayed / queue
│   │   ├── xlsx_report.py           # xuất báo cáo chi phí .xlsx
│   │   ├── slugify.py               # slug bóc dấu tiếng Việt (nguồn duy nhất)
│   │   └── hermes/                  # framework agent nội bộ
│   │
│   ├── mcp_servers/
│   │   ├── image_cut.py             # MCP server cắt ảnh sản phẩm
│   │   └── xanax_skills.py          # cầu nối MCP: phơi skill api/builtin cho CLI
│   │
│   ├── skills/                      # skill dạng prompt (markdown)
│   ├── tools/                       # builtin tool + script bảo trì
│   ├── scripts/smoke_hub.py         # Playwright: 12 tab + state + ảnh run cũ
│   ├── tests/                       # 334 test
│   └── data/                        # runtime — KHÔNG commit
│       ├── .secret_key              # ⚠ mất là mất hết token skill
│       ├── projects/                # archive từng lần chạy
│       ├── assets/  souls/  project_souls/  skill_souls/  training-images/
│       ├── legacy-static/           # ảnh cũ thời giao diện vanilla
│       └── mcp-images/              # tạo khi có tool MCP trả về ảnh
│
├── frontend/
│   ├── index.html
│   ├── vite.config.ts               # proxy /api và /ws tới :8000 khi dev
│   ├── package.json
│   ├── public/images/               # ảnh thương hiệu → dist/images
│   ├── scripts/                     # 4 script verify:* đọc DB + mã backend thật
│   ├── src/
│   │   ├── main.tsx                 # entry + import font @fontsource
│   │   ├── routes.tsx               # React Router
│   │   ├── api/                     # client.ts (một nơi duy nhất gọi API) + types
│   │   ├── ws/useWebSocket.ts       # hook chung cho cả 7 kênh
│   │   ├── store/                   # theme, ngôn ngữ, phiên
│   │   ├── components/              # Icon, Modal, Markdown, ChatAttach, Tooltip, Toast…
│   │   ├── i18n/                    # tooltips.ts, taskrunner.ts, workspace.ts
│   │   └── pages/
│   │       ├── login/  hub/  workspace/  taskrunner/
│   └── dist/                        # bản build có hash — KHÔNG commit
│
├── docs/
└── README.md
```

---

## Database — 30 bảng

**File:** `backend/hub/database.py` (schema + migration tự chạy lúc startup)

```
AUTH        users · sessions
NHÂN SỰ     agent_configs · departments · skills
DỰ ÁN       projects · work_items · task_alerts
QUY TRÌNH   workflow_tasks · workflow_runs · workflow_outputs
HỌP         meetings · meeting_messages
HUẤN LUYỆN  training_sessions · training_messages · xanax_notes
ĐÁNH GIÁ    benchmarks · benchmark_results
THÍ NGHIỆM  experiments · experiment_trials · experiment_judgements
MODEL       model_pool · model_usage · model_usage_hourly · model_call_log
TƯ LIỆU     knowledge_documents
TÀI SẢN     assets
OPS         ops_history
LEGACY      task_sessions · pipeline_logs
```

Vài điểm dễ sai:
- `agent_configs.model_pool_id` là **INTEGER FK** → `model_pool.id`. Cột `model` (string) chỉ còn để tương thích ngược, được derive tự động khi `list_agent_configs()` JOIN với pool. Đừng lưu model string thủ công.
- `workflow_tasks.graph_json` là **nguồn thật** của sơ đồ quy trình (node có toạ độ `x`/`y`, cạnh có nhánh `true`/`false`). `agents_json` là dạng tuần tự cũ, tự chuyển sang graph lần đầu mở.
- `workflow_outputs.status`: `done` | `error` — `error` khi provider trả `[Error]...` hoặc sinh ảnh thất bại.
- Skill **không** cấu hình model riêng: model luôn lấy từ nhân viên được gán, kể cả khi sinh ảnh.

---

## Xanax Tool Use

Xanax hành động bằng cú pháp nhúng cuối câu trả lời; server parse sau khi stream xong, thực thi, rồi gửi event `tool_executed` về client (tool call bị strip khỏi nội dung hiển thị và khỏi bản lưu DB).

```
[[XANAX:action|param1=value1|param2=value2]]
```

| Action | Params |
|---|---|
| `save_note` | `content=...` |
| `delete_note` | `id=N` |
| `create_work_item` | `project_id` · `title` · `description` · `priority` · `assignee` |
| `update_work_item` | `id` · `status` · `priority` · `assignee` |
| `trigger_workflow` | `task_id=N` |

Mỗi tin nhắn tới Xanax đều kèm snapshot DB tươi (`_build_live_context()` trong `api/websocket_training.py`). Không cần restart để Xanax biết dữ liệu mới.

Phía React, `stripToolSyntaxForDisplay()` (`components/Markdown.tsx`) giữ lại phần đuôi có thể là mảnh của marker (`[`, `[[`, `[[XA`…) khi stream — nếu không, cú pháp tool sẽ **nhấp nháy trên màn hình** đúng một khoảnh khắc giữa hai chunk rồi mới biến mất.

---

## Quy trình & Phòng họp

**Ngữ cảnh 3 lớp** khi chạy quy trình: mô tả dự án (brief cố định) → mô tả quy trình → input người dùng. Chỉ lớp cuối đổi mỗi lần chạy.

**Phát hiện lỗi:** `_is_error_output()` bắt `[Error]`, `[Hermes error:`, `[Xanax error:` → đánh dấu run `failed`. Trước đây provider trả lỗi dạng text kèm HTTP 200 thì run vẫn bị đánh dấu "Hoàn thành".

**Run sống lâu hơn kết nối.** Lần chạy nằm trong `_run_sessions` của tiến trình server và **chạy tiếp khi WebSocket đứt**. Client F5 xong phải gửi `attach` kèm `run_id` để nối lại — bỏ bước này là người dùng mất dấu một quy trình vẫn đang chạy.

**Trong phòng họp**, chỉ Xanax được kích hoạt quy trình. `_is_workflow_command()` nhận diện câu lệnh chạy quy trình (cố ý bắt rộng) và chặn định tuyến tắt về nhân viên — nếu không, lần gọi thứ hai sẽ bị nhân viên "trả lời lại" bằng kết quả bịa thay vì thật sự chạy. Prompt của nhân viên cũng nói rõ họ không có quyền này.

**Lưu trữ:** mỗi lần chạy được archive ra `backend/data/projects/<dự_án>/<quy_trình>/<yyyymmdd_hhmmss>/` — ảnh ghi thẳng vào đó lúc sinh, text + `run_info.json` ghi thêm khi kết thúc. DB vẫn là nguồn hiển thị chính.

---

## Windows subprocess — quy tắc bắt buộc

`asyncio.create_subprocess_exec` **không hoạt động** dưới uvicorn trên Windows. Mọi subprocess phải đi qua `api/agents/subprocess_util.py` → `stream_proc` (dùng `subprocess.Popen` trong `threading.Thread`). Không có ngoại lệ.

MCP stdio server thì khác — Python MCP SDK tự dùng Windows Job Object (`KILL_ON_JOB_CLOSE`), đã kiểm chứng bằng cách hard-kill tiến trình cha: 0 tiến trình mồ côi. Không cần cơ chế dọn PID thủ công.

Prompt phải đi qua **stdin**, không qua `argv`. Prompt của agent dài hàng nghìn ký tự, nhiều dòng, có tiếng Việt và dấu nháy — nhét vào dòng lệnh là hỏng escaping trên Windows.

---

## Gọi model qua CLI gói thuê bao

Nhân viên có thể chạy bằng **tiến trình CLI đã đăng nhập gói** (`claude`, `codex`) thay vì gọi HTTP tới provider trung gian. Không có API key nào trong cấu hình, nên không có key nào để lộ hay bị thu hồi, và chi phí nằm trong gói thuê bao thay vì tính theo token.

Thêm ở **Bộ não AI → Thêm model → tab "Qua CLI (gói thuê bao)"**:

| Ô | Ý nghĩa |
|---|---|
| Engine | `claude_cli` (gói Claude) hoặc `codex_cli` (gói ChatGPT) |
| Model ID | `claude-haiku-4-5`, `gpt-5.5`… — truyền thành `--model`/`-m` |
| Thư mục tài khoản | `CLAUDE_CONFIG_DIR` / `CODEX_HOME`. Để trống = tài khoản mặc định. **Mỗi tài khoản một thư mục** — đây là cách chạy nhiều gói song song trên một máy, và cách xoay tài khoản khi một gói cạn hạn mức phiên |

Gán model đó cho nhân viên như bình thường (Nhân sự → chọn agent → Model). Phòng họp và Quy trình tự động dùng, vì cả hai đều đi qua `stream_from_agent_models()`. Thứ tự ưu tiên nhiều model vẫn hoạt động: model CLI hết hạn mức phiên thì tự chuyển sang model kế tiếp.

**Điều quan trọng nhất — `build_clean_env()` trong `core/cli_provider.py`.** CLI ưu tiên biến môi trường hơn đăng nhập gói: nếu tiến trình server có `ANTHROPIC_BASE_URL`/`OPENAI_BASE_URL` trỏ về gateway, tiến trình con **âm thầm chui qua gateway đó** mà không báo lỗi gì. Nên mọi lần spawn CLI đều chạy bằng env đã xoá sạch nhóm biến này. Đừng bỏ qua nó khi thêm engine CLI mới.

Hai giới hạn phải biết trước:

- **Tool-calling đi bằng MCP, không phải `tools[]`.** CLI không nhận `tools[]` theo JSON Schema. Kỹ năng của nhân viên được phơi ra cho `claude` qua MCP:

  | Loại kỹ năng | Đường đi tới CLI |
  |---|---|
  | `custom` | Nằm trong system prompt, không phải tool — luôn chạy được |
  | `api`, `builtin` | Qua cầu nối `mcp_servers/xanax_skills.py` (stdio), dùng lại `tool_registry` nên hành vi giống hệt đường HTTP |
  | `mcp` | Khai báo **thẳng** cho CLI. Đi vòng qua cầu nối sẽ thành MCP-trong-MCP: mở phiên con mất vài giây, đủ để CLI bỏ cuộc và báo server `pending` |

  Hai chi tiết đã phải trả giá mới tìm ra: schema tool lấy từ `ToolDefinition.to_schema()` (để FastMCP tự suy từ chữ ký hàm sẽ ra một ô `kwargs` vô nghĩa), và **`ToolSearch` phải được cho phép** — CLI hoãn nạp schema MCP và bắt model gọi `ToolSearch` để lấy, tắt nó đi là nhân viên báo "công cụ chưa khả dụng" rồi bó tay.

  `codex_cli` **chưa** có cầu nối, nên vẫn không gọi được công cụ.

- **Log thành công phải dựa trên việc đã làm.** `stream_from_agent_models()` bỏ qua model không gọi được công cụ khi có `tools`, và báo lỗi rõ nếu nhân viên không còn model nào dùng được. Bước quy trình còn kiểm thêm một tầng: nhân viên **có công cụ mà không gọi cái nào thì bước TRƯỢT**, vì không có bằng chứng việc đã xảy ra — chỉ có lời nhân viên tự thuật.

  **Chỉ kỹ năng loại `api` mới là việc bắt buộc** (`_required_tool_names()`): người dùng cấu hình hẳn một endpoint rồi giao cho nhân viên đúng việc gọi nó. `mcp`/`builtin` là công cụ dùng khi cần — bắt buộc chúng là đánh trượt oan, đã gặp thật: nhân viên tạo ảnh có kèm skill MCP cắt ảnh nhưng lần chạy đó không cần cắt, bài viết và ảnh đều giao đủ mà quy trình vẫn dừng.

  Sổ bằng chứng là `collect_tool_invocations()` (`core/skill_tools.py`), ghi ở đúng nơi tool được thực thi: `_stream_openai` cho đường HTTP, và sự kiện `tool_use` của CLI cho đường MCP. Chỉ tool đi qua MCP mới được tính — tool nội bộ của CLI như `ToolSearch` thì không, nếu không một nhân viên tra cứu rồi bịa kết quả vẫn qua được cửa.

  Đây là hành vi cố ý sau sự cố thật: nhân viên đăng Facebook chạy trên model CLI, tool bị bỏ im lặng, nhân viên vẫn sinh ra chữ và bước quy trình ghi "Đã chạy xong" trong khi **không có request nào tới Facebook** — chỉ mở fanpage ra mới biết. Thà hỏng ồn ào còn hơn thành công giả.

- **Codex CLI sinh được ảnh.** Bật bằng `--enable image_generation` — Codex có skill hệ thống `imagegen` chạy trong gói ChatGPT, nên **không cần mua image model riêng**. `_maybe_generate_image()` tự dùng đường này cho entry `codex_cli`.

  Khác đường HTTP ở một điểm: Codex **tự chọn nơi lưu** (`~/.codex/generated_images/<thread_id>/call_*.png`), nên phải bắt `thread_id` từ sự kiện `thread.started` rồi copy về thư mục của lần chạy. Codex không trả `usage` cho ảnh nên bảng chi phí ghi 0 — đúng bản chất, ảnh nằm trong gói chứ không tính theo token.

  `claude_cli` thì **không** sinh được ảnh, vẫn bị bỏ qua ở bước này.

- **Model trong pool chỉ để trả lời chữ.** Bộ công cụ của Claude Code bị tắt (`_CHAT_ONLY_DISALLOWED_TOOLS`) — vừa đúng vai, vừa cắt ~44% token ngữ cảnh mỗi lượt (đo thật: 20.161 → 11.383), đáng kể với hạn mức 5 giờ của gói. Đường cần thao tác file là `api/agents/claude_runner.py`.

CLI trả về số token thật trong sự kiện kết thúc, nên trang Chi phí và giới hạn dùng/ngày vẫn đo đúng chứ không phải ước lượng theo ký tự.

---

## Kiểm thử

```powershell
cd D:\xanax\backend
python -m pytest tests/ -q            # 334 passed
python scripts\smoke_hub.py           # Playwright trên trình duyệt thật
```

```powershell
cd D:\xanax\frontend
npm run typecheck
npm run verify:graphs
npm run verify:workflow-protocol
npm run verify:meeting-protocol
npm run verify:hub-integration
```

`tests/test_api.py` có `anon_client` (không đăng nhập) và `client` (tự tạo rồi xoá user tạm) — `TestAuthGuard` kiểm tra đúng cả hai chiều: endpoint bị chặn khi không có phiên, và chạy được khi có.

**Không có test tự động nào cho WebSocket.** Logic WS được kiểm bằng cách gọi thẳng hàm nội bộ với `httpx.AsyncClient` đã monkeypatch. Đừng giả định "pytest xanh nghĩa là WS không hỏng" — bốn script `verify:*` phía frontend chính là để bù chỗ này.

---

## Triển khai production

Runbook Ubuntu 24.04 đầy đủ nằm ở **[deploy/README.md](deploy/README.md)**.
Kiến trúc chốt: Internet/DNS → Caddy `:443` (TLS + WebSocket) → một process
FastAPI trên `127.0.0.1:8000` → SQLite và `backend/data`. App chạy bằng user
`xanax` riêng, do systemd quản lý; cổng 8000 không public.

---

## Checklist trước khi deploy

Đã xong:
- [x] Xác thực toàn bộ `/api/*` và `/ws/*`, gồm cả WebSocket
- [x] Mã hoá `api_key` / `token` khi lưu, che khi trả về API
- [x] Nén gzip cho mọi response
- [x] Frontend tách chunk theo route; bundle vào đầu 232 kB → **74,6 kB gzip**
- [x] Bản build **không gọi ra Internet lần nào** — font tự chứa, không CDN
- [x] 334 test tự động + 4 script verify đối chiếu hợp đồng FE/BE
- [x] Hạ tầng Ubuntu: systemd + Caddy/TLS + backup/restore — xem `deploy/`

Còn phải làm:
- [ ] Đặt `HUB_SECRET_KEY` và `HUB_API_KEY` thật (đang là placeholder)
- [ ] `HUB_DEBUG=false` (đang `true` → uvicorn bật reload, và `cors_origins` thành `["*"]`)
- [ ] Chuyển sang Postgres nếu cần nhiều người dùng đồng thời

---

## Gỡ lỗi nhanh

| Triệu chứng | Nguyên nhân thường gặp |
|---|---|
| Mở `localhost:8000` ra trang trắng | Chưa `npm run build`, hoặc `frontend/dist/` bị xoá |
| Sửa React mà không thấy đổi | Đang xem cổng 8000 (bản build) thay vì 5173 (bản dev) |
| `ModuleNotFoundError: cryptography` | `pip install -r requirements.txt` |
| Cấu hình `.env` như vô tác dụng | Chạy `python main.py` từ ngoài `backend/`. Phải `cd backend` trước |
| Dev bị 401 khắp nơi | Proxy trong `vite.config.ts` sai. **Đừng** sửa bằng cách mở CORS |
| LLM không phản hồi | Kiểm `GET /api/health` và `HUB_LLM_API_BASE` trong `.env` |
| Model Pool báo `404 no active credential` | Credential phải cấu hình ở dashboard của provider, không phải trong Xanax |
| Model CLI báo `model requires a newer version of Codex` | Điền Model ID rõ ràng (`gpt-5.5`, `gpt-5.4`) thay vì để trống, hoặc nâng cấp CLI |
| Model CLI báo `not supported when using Codex with a ChatGPT account` | Model đó chỉ dùng được với API key. Đổi model khác |
| Model CLI bỗng lỗi xác thực dù không đổi gì | Kiểm biến rò rỉ: `Get-ChildItem env: \| Where-Object Name -match 'ANTHROPIC\|OPENAI'` |
| Model CLI hết hạn mức phiên 5 giờ | Đổi ô "Thư mục tài khoản" sang thư mục gói khác. Không cần restart |
| Nhân viên báo "đã đăng" nhưng thực tế không có gì | Không còn xảy ra âm thầm: bước sẽ trượt kèm lý do. Kiểm `collect_tool_invocations()` |
| Bước trượt vì `KHÔNG gọi công cụ` dù đã giao đủ việc | Chỉ kỹ năng `api` mới bắt buộc. `mcp`/`builtin` mà trượt là lỗi — xem `_required_tool_names()` |
| MCP báo `status: pending`, tool không hiện | Server khởi động chậm (thường do MCP lồng MCP), hoặc `ToolSearch` bị tắt |
| Skill MCP không thấy tool nào | Bấm "Kiểm tra kết nối". Sai `target` hoặc sai Python venv là nguyên nhân phổ biến nhất. Vừa dời thư mục dự án? Chạy `tools/migrate_mcp_server_paths.py` |
| MCP báo `'Server' object has no attribute 'list_tools'` | SDK `mcp` 2.x đã bỏ decorator này. Ghim `mcp<2` |
| Nhân viên CLI kể việc sắp làm thay vì làm | Đã chặn bằng `_DELIVERABLE_ONLY` + `--permission-mode default` (KHÔNG dùng `plan`) |
| Sinh ảnh thất bại | Model text không hỗ trợ `/images/generations` — cần thêm image model vào pool |
| F5 xong mất dấu quy trình đang chạy | Client không gửi `attach` kèm `run_id`. Run vẫn đang chạy trong server |
| Preflight CORS bị 401 | Ai đó đảo thứ tự `add_middleware` — AuthGuard phải thêm TRƯỚC CORS |

---

## Quy ước khi sửa code

### Backend
1. Thêm route mới → đăng ký trong `create_app()` (`hub/server.py`). Middleware tự bảo vệ, không cần thêm `Depends`.
2. Thêm bảng DB mới → thêm vào `init_db()` **và** viết migration trong `database.py`.
3. Cần slug? Dùng `core/slugify.py`. Đừng viết lại bằng JS — bản Python bóc dấu tiếng Việt (`cắt ảnh` → `cat_anh`), bản JS ngây thơ ra `c_t_nh` và tên tool lệch nhau.
4. Mọi subprocess đi qua `stream_proc`.
5. Codex CLI nhận prompt qua **stdin**, không qua CLI arg.
6. Pipeline chạy bằng `asyncio.create_task` — không block vòng lặp receive của WebSocket.
7. Đường dẫn SOUL.md luôn qua `_soul_path()`, không hardcode.
8. Thêm khoá bí mật mới vào skill config → thêm tên khoá vào `SECRET_CONFIG_KEYS`.
9. Thêm phụ thuộc Python → thêm vào `requirements.txt`, kể cả khi máy bạn đã có sẵn.

### Frontend
10. Mọi lời gọi API đi qua `src/api/client.ts`. Đừng `fetch` trần — nơi đó xử lý 401, 204 và bóc `.detail`.
11. Mọi WebSocket đi qua `src/ws/useWebSocket.ts`. Mã đóng `1008` là hết phiên: về login, **không** thử lại.
12. Đổi `graph_json` hay giao thức WS → chạy `npm run verify:*` trước khi commit.
13. Chuỗi hiển thị phải có cả `vi` và `en` (từ điển `pages/hub/i18n.ts`, `src/i18n/<trang>.ts` hoặc `vi ? … : …`).
14. Route nặng thì `React.lazy()`. React Flow và Chart.js chỉ một tab dùng tới.
15. Xuống dòng bình thường. Nhồi cả component vào một dòng là diff vô dụng và trace lỗi vô nghĩa.

### Chung
16. Cuối mỗi phiên làm việc: cập nhật README này cho khớp thực tế.
17. Đổi số phiên bản → sửa **hai** chỗ: `backend/hub/config.py` và `backend/pyproject.toml`.

---

## Đánh số phiên bản

Theo [SemVer](https://semver.org): `MAJOR.MINOR.PATCH`. "Hợp đồng" ở đây là những
thứ bên ngoài phụ thuộc vào — không phải giao diện.

| Bậc | Khi nào tăng | Ví dụ trong dự án này |
|---|---|---|
| **MAJOR** | Phá vỡ tương thích | Đổi/xoá endpoint, đổi hình dạng message WebSocket, đổi schema DB hay `graph_json` theo kiểu dữ liệu cũ đọc không ra, đổi cấu trúc thư mục lớn |
| **MINOR** | Thêm khả năng mới, vẫn tương thích ngược | Thêm endpoint, thêm loại node quy trình, thêm tính năng người dùng thấy được, đổi lớn về giao diện |
| **PATCH** | Chỉ sửa lỗi và tài liệu | Sửa lỗi hiển thị, sửa tương phản màu, sửa chú thích, thêm phụ thuộc còn thiếu |

**Nguồn duy nhất là `Settings.version` trong `backend/hub/config.py`.** Nó chảy ra
banner lúc khởi động, `GET /api/health`, `GET /api/version` và `/api/docs`. `backend/pyproject.toml`
phải khai cùng số — đó chỉ là metadata đóng gói, không phải nguồn.

Đừng khai `HUB_VERSION` trong `.env`: `.env` **đè lên** giá trị trong code, nên
sửa `config.py` sẽ không có tác dụng gì mà cũng không báo lỗi.

### Lịch sử

| Phiên bản | Nội dung |
|---|---|
| `0.1.0` | Bản đầu — FastAPI + SQLite + giao diện vanilla JS |
| `2.0.0` | Tách backend/frontend, viết lại giao diện bằng React + TypeScript (7 giai đoạn). API, WebSocket và schema DB giữ nguyên |
| `2.1.0` | Hệ màu dùng chung cho cả 4 trang · cỡ chữ chỉnh bằng một biến · khôi phục bộ chọn hình đại diện (30 hình, 20 màu) · font tự chứa · sửa tương phản đạt WCAG AA · nạp `XANAX_SECRET_KEY` từ `.env` · WebSocket trả đúng mã đóng `1008` |
| `2.2.0` | Soul theo dự án và theo kỹ năng · ghép ảnh sản phẩm lên nền sinh sẵn (`image_compose.py`) · chế độ ảnh và cổng chọn nguồn ảnh trong quy trình · chọn từng tool của skill MCP cho nhân viên · buổi dạy gắn dự án và cấp tool thật · 4 cột DB mới (đều có giá trị mặc định) |
| `2.3.0` | Thí nghiệm tự cải thiện: ablation ba tầng tri thức trên cùng model, có giám khảo chấm mù · 3 bảng DB mới · tooltip và toast dùng chung · i18n tách theo trang · bộ chọn lịch chạy cho quy trình · gộp tab Bộ não AI thành 3 mục: Model Pool, Đánh giá model, Thí nghiệm tự cải thiện |
| `2.4.0` | Sẵn sàng triển khai: chặn khởi động production khi secret còn mặc định · cookie phiên bật `Secure`, tắt API docs khi `HUB_DEBUG=false` · rate limit đăng nhập theo IP + tài khoản, chỉ tin `X-Forwarded-For` khi khai báo có proxy · readiness probe kiểm tra thật database/scheduler/hàng đợi · đồng bộ dependency `pyproject.toml` với `requirements.txt` · thư mục cấu hình Hermes phân giải được trên Linux · bộ cài `deploy/` cho Ubuntu 24.04 (systemd, Caddy, backup/restore, runbook) · test chạy trên DB tạm thay vì database thật |
| `2.4.1` | Ba lỗi lộ ra khi triển khai thật lên Ubuntu: bộ test không còn đọc `.env` của máy đang chạy (trên server cấu hình production nó báo 13 lỗi giả) · `/api/health` đo uptime bằng đồng hồ đơn điệu nên NTP chỉnh giờ không làm uptime âm · `deploy/*.sh` được đặt bit thực thi trong git để clone trên Linux chạy được (systemd báo `203/EXEC` mà không nhắc gì tới quyền file) |
| `2.5.0` | Chống mất dữ liệu: backup đẩy lên Cloudflare R2 qua rclone remote `crypt` (bắt buộc mã hóa vì archive chứa `XANAX_SECRET_KEY`) và tự đối chiếu kích thước bản trên cloud · cảnh báo Telegram khi web chết, backup hỏng hoặc ổ đầy, có máy trạng thái chống spam · `drill-restore.sh` diễn tập khôi phục vào `/opt/xanax-drill` cổng 8001, không chạm production · `restore.sh` có rào chắn bắt `APP_ROOT` và `SERVICE_NAME` khớp cặp · `xanax.service` nới `StartLimitBurst` vì mặc định 5 lần/10 giây có thể làm unit nằm chết vĩnh viễn · Độ bền: SQLite bật WAL và `busy_timeout` cho 137 chỗ mở kết nối · subprocess `claude`/`codex` có timeout và thu hoạch cả tiến trình con khi hết giờ hoặc client bỏ đi · giới hạn RAM theo cgroup để OOM không bắn nhầm Caddy hay sshd · `requirements.lock` sinh từ venv production |
| `2.6.0` | Cảnh báo credential `claude`/`codex` hết hạn: `POST /api/health/providers` thử các entry `claude_cli`/`codex_cli` trong model pool, bắt buộc xác thực và không nằm trong allowlist công khai của `AuthGuard` · `xanax-provider-check` chạy hằng ngày, bắt được tình trạng mọi agent đều gãy dù `/api/health/ready` vẫn xanh cả bốn check · Skill cắt ảnh sản phẩm chạy trên Linux: target MCP dùng alias đa nền tảng `xanax://image-cut`, launcher tự phân giải interpreter của venv `rembg` riêng · SDK MCP chỉ kế thừa whitelist biến môi trường không có `HOME`, khiến `rembg` không tìm thấy cache model, nên launcher truyền tường minh `HOME`/`U2NET_HOME` |
| `2.6.1` | Siết route bắt-tất-cả của SPA sau khi log production cho thấy máy quét gọi `/.git/config` và nhận 200: segment bắt đầu bằng dấu chấm trả 404 (trừ `.well-known`), yêu cầu trông như file chỉ được phục vụ khi đích đã `resolve()` vẫn nằm trong `dist` · Không có dữ liệu bị rò rỉ vì phản hồi trước đây là `index.html`, nhưng bỏ 200 giả để máy quét không dò tiếp và làm bẩn access log · Sửa file ở gốc `dist` như `favicon.ico`, `robots.txt` trả đúng nội dung thay vì HTML |
| `2.6.2` | Launcher MCP cắt ảnh không còn `resolve()` đường dẫn Python của venv `rembg`: `bin/python` là symlink tới interpreter hệ thống, đi theo nó làm `execv` chạy Python hệ thống và mất `pyvenv.cfg`/site-packages, khiến `image_cut.py` chết với `ModuleNotFoundError: mcp` dù cả hai venv đều có gói · Sửa khối kiểm tra model trong runbook: glob sai tầng từng in `Cache` rỗng dù model đã tải đúng |
| `2.6.3` | Launcher MCP cắt ảnh tự đặt thư mục làm việc về `backend/` trước khi exec: `FastMCP()` dò `.env` theo cwd, nên chạy từ thư mục không đọc được như `/root` dưới `sudo -u xanax` làm pydantic-settings chết bằng `PermissionError` thay vì bỏ qua · Chọn `backend/` vì `core/image_gen.py` còn hướng dẫn model lưu vào đường dẫn tương đối `data/assets`, cố định cwd giữ đúng ngữ nghĩa production |
| `2.7.0` | Giới hạn cgroup được ghi cố định vào `deploy/xanax.service` (`MemoryHigh=4.5G`/`MemoryMax=5G`) thay vì chỉ dùng `systemctl set-property --runtime`: cấu hình trong `/run` mất sau reboot, trả máy về 3.5G và tái diễn sự cố đứng máy; thêm `MALLOC_ARENA_MAX=2` để hạn chế allocator giữ RAM · Skill cắt ảnh tắt CPU memory arena của onnxruntime qua `sess_opts`, gọi `gc.collect()` + `malloc_trim(0)` sau mỗi lần cắt và xoá cache session sau 600 giây nhàn rỗi, vì `MCPConnection` sống suốt vòng đời app nên tiến trình không bao giờ tự thoát; trên production, RSS sau 30 giây nghỉ giảm từ khoảng 4,5 GB xuống 127–138 MiB · Chốt kiểm tra RAM trước inference lấy giá trị nhỏ hơn giữa `MemAvailable` và phần cgroup v2 còn lại, từ chối kèm thông báo hữu ích thay vì để kernel OOM-kill tiến trình web; đo được `birefnet-general-lite` đạt đỉnh 5.562–5.628 MiB còn `u2netp` chỉ 518 MiB · ONNX của birefnet có input cố định `[1, 3, 1024, 1024]`, nên thu nhỏ ảnh đầu vào không hạ được đỉnh RAM—ghi lại đường cụt này để không lặp lại chi phí thử nghiệm · `backend/requirements.lock` được sinh từ venv production với 54 gói, gỡ nút thắt `test -s` từng chặn mọi lần deploy |
| `2.8.0` | Tiêu đề tab trình duyệt đổi theo route thay vì kẹt ở chuỗi “Xanax — Đăng nhập” ghi cứng trong `index.html`; tab `/hub` dùng lại chính nhãn i18n của sidebar để hai nơi không trôi khỏi nhau · Năm trong footer lấy từ `getFullYear()` qua placeholder i18n thay vì ghi cứng `© 2025`, để sang năm không phải sửa lại · Thêm `GET /api/version` để trang đăng nhập đọc số phiên bản lúc chạy thay cho chuỗi `v1.0` ghi cứng đã lạc hậu nhiều bản; cố ý không nhúng lúc build vì quy trình deploy chỉ build lại frontend khi có động vào `frontend/src`, nên bản chỉ đổi backend sẽ để số hiển thị lạc hậu; mã commit chỉ trả cho request đã xác thực để không phơi dấu vân tay triển khai ra Internet — đây là khả năng mới tương thích ngược nên tăng MINOR thay vì PATCH |
| `2.8.1` | VPS được nâng từ 6 GB lên 8 GB (MemTotal thật 7,75 GiB) để giữ được model `birefnet-general-lite`, nên `deploy/xanax.service` nới `MemoryHigh` từ 4.5G lên 6.5G và `MemoryMax` từ 5G lên 7G · Hai mức được chọn từ số đo thật: cgroup còn trống lúc nghỉ khoảng 6,7 GiB, vượt ngưỡng 6 GiB mà lớp chặn RAM đòi hỏi; đỉnh inference 5,5 GiB cộng 288 MiB của web vẫn dưới `MemoryHigh`, nên không lượt cắt nào bị throttle · Lý do không được hạ trần tùy tiện được ghi ngay trong unit: lớp chặn so ngưỡng với phần CÒN LẠI của cgroup chứ không phải tổng RAM — đợt này chỉ chỉnh cấu hình triển khai và tài liệu, không đổi hợp đồng API nên tăng PATCH |
| `2.8.2` | MCP cắt ảnh chết ngay lúc khởi động trên production với `ModuleNotFoundError: No module named 'mcp_servers'`, hỏng từ bản 2.7.0 khi phần hình học được tách sang `image_cut_helpers.py`: launcher chạy `image_cut.py` NHƯ MỘT SCRIPT nên `sys.path[0]` là thư mục chứa script (`backend/mcp_servers`) chứ không phải `backend`, và `os.chdir` về `backend` không giúp gì vì cwd không nằm trong `sys.path` · Toàn bộ test vẫn xanh suốt thời gian đó vì `conftest` thêm sẵn `backend/` vào `sys.path`, tức đường chạy trong test khác đường chạy thật — vì vậy bản vá thêm `backend/` vào đường import ngay trong script và đi kèm một test CHẠY THẬT `image_cut.py` bằng tiến trình con từ cwd bất kỳ, với module giả cho `rembg`/`onnxruntime`/`mcp`; đã kiểm chứng test đỏ khi gỡ dòng vá · Đây chỉ là sửa lỗi khởi động, không đổi hợp đồng API nên tăng PATCH |

---

## Giấy phép

Dự án cá nhân, chưa công bố giấy phép.

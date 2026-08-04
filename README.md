# Xanax — AI Agent ERP

Xanax là hệ thống quản lý **nhân viên AI như một công ty**: tuyển (tạo agent), giao việc, xếp thành quy trình nhiều bước, họp bàn, nghiệm thu kết quả, và theo dõi chi phí token.

Chạy hoàn toàn trên máy cá nhân (Windows), viết bằng **FastAPI + SQLite + vanilla JS**, gọi LLM qua bất kỳ endpoint nào tương thích OpenAI.

```powershell
cd D:\xanax
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # sửa HUB_SECRET_KEY trước khi dùng thật
python main.py
```

Mặc định: `http://localhost:8000` → đăng nhập → `/hub`. API docs tại `/api/docs`.

---

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

---

## 12 tab trong `/hub`

| Tab | URL | Nội dung |
|---|---|---|
| Tổng quan | `/hub` | Thẻ thống kê, widget hoạt động, cảnh báo, biểu đồ chi phí |
| Nhân sự | `/hub/agents` | CRUD agent, gán model + kỹ năng + phòng ban, xem `soul.md` |
| Kỹ năng | `/hub/skills` | CRUD skill 3 loại: `custom` / `api` / `mcp` — có nút kiểm tra kết nối |
| Dự án | `/hub/tasks` | Kanban công việc, matcher gợi ý người phù hợp, cảnh báo không khớp |
| Họp | `/hub/meeting` | Phòng họp nhiều agent, realtime qua WebSocket |
| Huấn luyện | `/hub/train` | Chat với Xanax, dạy quy tắc → lưu vào `SOUL.md` |
| Quy trình | `/hub/company-runner` | Thiết kế + chạy quy trình nhiều bước, duyệt từng output |
| Tác vụ tự động | `/hub/auto-runner` | Quy trình chạy theo lịch cron / webhook |
| Tài sản | `/hub/assets` | File upload + kết quả quy trình đã lưu trữ, tải về |
| Model Pool | `/hub/model` | Khai báo model, giới hạn dùng/ngày, test kết nối, biểu đồ top 10 |
| Chi phí | `/hub/cost` | Thống kê token/chi phí, xuất báo cáo `.xlsx` |
| Cài đặt | `/hub/settings` | Cấu hình chung |

Ngoài `/hub` còn: `/workspace` (chat huấn luyện toàn màn hình), `/taskrunner` (quy trình toàn màn hình, cũng dùng nhúng iframe qua `?embed=1`).

---

## Hệ thống Skill — 3 loại

Skill là "kỹ năng nghề" gán cho nhân viên. Khi nhân viên chạy, mọi skill được gán sẽ thành **tool** mà model gọi được.

### 1. `custom` — prompt thuần
Nội dung file markdown trong `skills/`, nhét vào system prompt. Không gọi ra ngoài.

### 2. `api` — HTTP endpoint
Khai báo method / URL / headers / body template. `core/skill_tools.py` sinh tool động, đăng ký vào `ToolRegistry`.

Có xử lý riêng cho Facebook Page: tự đổi sang `/photos` khi bài đăng kèm ảnh do quy trình vừa tạo.

### 3. `mcp` — Model Context Protocol
`core/mcp_client.py` là MCP client thật, hỗ trợ 3 transport: **stdio**, **http** (streamable), **sse**.

```
Skill "cat_anh_san_pham"  (type: mcp)
  ├─ transport: stdio
  ├─ target: <python.exe venv rembg> d:\xanax\mcp_servers\image_cut.py
  └─ tools: ["cut_product", "cut_product_batch"]   ← chọn từng tool, không phải all-or-nothing
```

Chi tiết đáng lưu ý:
- **Một thẻ skill chứa nhiều tool.** UI hiện danh sách tool kèm checkbox; bỏ chọn tool nào thì tool đó không được đăng ký.
- **Đổi lựa chọn tool không cần kết nối lại** — chỉ đăng ký lại registry (0.01s thay vì ~7s).
- `tools: []` (bỏ chọn hết) khác với không có khoá `tools` (lấy tất cả). Đây là phân biệt cố ý.
- Kết nối được giữ bền bởi một supervisor task; `mcp_manager.close_all()` chạy khi server tắt.
- Tool trả về ảnh (`ImageContent`) được ghi ra `data/mcp-images/YYYYMMDD/` và trả về đường dẫn file.
- Tiền tố tên tool do backend sinh (`core/slugify.py`, có bóc dấu tiếng Việt) và trả về qua `GET /api/tools/mcp/status` — **frontend không được tự slugify lại**.

### MCP server có sẵn: `mcp_servers/image_cut.py`

Cắt ảnh sản phẩm: tách nền → cắt sát viền → chừa lề → đưa về tỉ lệ khung bài đăng.

```
cut_product(input_path, output_path, model="u2netp",
            padding_percent=2.0, ratio="", background="transparent",
            alpha_matting=False)
cut_product_batch(...)
```

Chạy bằng Python của venv `rembg`, **không phải** venv xanax. Model mặc định `u2netp`: đo thực tế trên máy này 0.44s/ảnh, ~657MB RSS — nhanh gấp đôi và nhẹ hơn `u2net` (0.97s, 985MB).

---

## Bảo mật

### Gác xác thực — `api/auth_guard.py`

ASGI middleware thuần **mặc định ĐÓNG**: mọi `/api/*` và `/ws/*` đều yêu cầu phiên đăng nhập, trừ danh sách mở tường minh.

```python
_PUBLIC_EXACT   = {"/api/auth/login", "/api/auth/logout", "/api/auth/me",
                   "/api/health", "/api/health/ready"}
_PUBLIC_PREFIXES = ("/api/workflow/hooks/",)   # webhook có token riêng trong URL
_GUARDED_PREFIXES = ("/api/", "/ws/")
```

Hai lựa chọn thiết kế có chủ ý:
- **Middleware thay vì `Depends` từng router** — route mới thêm sau tự động được bảo vệ; kiểu `Depends` thì mỗi router mới là một cơ hội quên.
- **ASGI thuần thay vì `@app.middleware("http")`** — cái sau chỉ chạy với scope `http`, WebSocket sẽ lọt lưới, mà `/ws/meeting` chính là nơi chứa nội dung họp và quyền kích hoạt quy trình.

**Thứ tự middleware trong `hub/server.py` là quan trọng:**

```python
app.add_middleware(AuthGuardMiddleware)   # thêm TRƯỚC → nằm trong
app.add_middleware(CORSMiddleware, ...)   # thêm SAU  → nằm ngoài
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

CORS phải nằm ngoài AuthGuard vì preflight `OPTIONS` không mang cookie — nếu ngược lại, mọi preflight sẽ bị chặn 401.

### Mã hoá bí mật khi lưu — `core/secret_crypto.py`

AES-256-GCM cho các khoá nhạy cảm trong `skills.config_json`:

```
enc:v1:<base64(nonce || ciphertext)>
SECRET_CONFIG_KEYS = ("api_key", "token")
```

- Khoá lấy từ `XANAX_SECRET_KEY`, không có thì tự sinh vào `data/.secret_key`.
- API trả về giá trị đã che (`••••••••`); khi lưu, giá trị che được merge lại thành giá trị cũ — sửa skill không làm mất token.
- Đây là bảo vệ **dữ liệu khi nằm yên**, không phải bảo vệ quyền truy cập API. Ai qua được `auth_guard` vẫn dùng được skill.
- Di trú dữ liệu cũ: `python tools/encrypt_existing_secrets.py` (mặc định chỉ xem trước, `--apply` để ghi, tự backup DB và kiểm tra giải mã khớp).

### Phiên đăng nhập
TTL 8h · idle timeout 15 phút (client) · purge cron 30 phút · cookie `xanax_session` (HttpOnly, SameSite=strict) · mật khẩu PBKDF2-HMAC-SHA256 260.000 vòng · mọi phiên bị xoá khi server restart.

---

## Cấu trúc thư mục

```
xanax/
├── main.py                      # uvicorn runner + banner + tự mở trình duyệt
├── hub/
│   ├── server.py                # create_app(): routes, middleware, lifespan, static
│   ├── config.py                # Pydantic Settings (env prefix HUB_)
│   ├── database.py              # aiosqlite — toàn bộ DB operations + migration
│   └── events.py                # event bus nội bộ
├── api/
│   ├── auth_guard.py            # gác xác thực /api/* và /ws/*
│   ├── websocket.py             # /ws/chat
│   ├── websocket_training.py    # /ws/training — live context + Xanax tool use
│   ├── websocket_workflow.py    # /ws/workflow — chạy quy trình nhiều bước
│   ├── websocket_meeting.py     # /ws/meeting — phòng họp nhiều agent
│   ├── websocket_benchmark.py   # /ws/benchmark
│   ├── websocket_task.py
│   ├── agents/
│   │   ├── subprocess_util.py   # subprocess an toàn trên Windows (BẮT BUỘC dùng)
│   │   ├── claude_runner.py     # wrapper Claude CLI (stream-json)
│   │   └── codex_runner.py      # wrapper Codex CLI (prompt qua stdin)
│   └── routes/                  # 20 module: auth, agents, skills_mgmt, projects,
│                                # meetings, workflow, model_pool, knowledge, ops,
│                                # assets, departments, tools, ...
├── core/
│   ├── mcp_client.py            # MCP client: stdio/http/sse, chọn tool, ảnh
│   ├── skill_tools.py           # skill type "api" → tool động
│   ├── secret_crypto.py         # AES-256-GCM cho api_key/token
│   ├── model_pool_bridge.py     # gọi model qua pool, LimitExceededError
│   ├── hermes_bridge.py         # LLM client + phiên chat in-memory
│   ├── image_gen.py             # sinh ảnh, ImageGenError với lỗi cụ thể
│   ├── agent_soul.py            # soul.md riêng cho từng nhân viên
│   ├── soul_sync.py             # SOUL.md của Xanax
│   ├── project_storage.py       # lưu trữ kết quả run ra ổ đĩa theo cây thư mục
│   ├── rag.py                   # truy hồi tài liệu bằng keyword overlap
│   ├── matcher.py               # khớp nhân viên ↔ công việc
│   ├── orchestrator.py          # điều phối agent chạy ngầm
│   ├── scheduler.py             # APScheduler: cron / delayed / queue
│   ├── xlsx_report.py           # xuất báo cáo chi phí .xlsx
│   ├── slugify.py               # slug có bóc dấu tiếng Việt (nguồn duy nhất)
│   └── hermes/                  # framework agent nội bộ: agent, planner,
│                                # memory, context, tool_registry
├── mcp_servers/
│   └── image_cut.py             # MCP server cắt ảnh sản phẩm
├── dashboard/
│   ├── login.html · index.html · workspace.html · taskrunner.html
│   ├── hub.html                 # khung SPA
│   └── static/
│       ├── hub.css              # ~83 KB — tách khỏi hub.html
│       ├── hub.js               # ~239 KB — tách khỏi hub.html, nạp defer
│       └── images/
├── tools/                       # builtin tools + script bảo trì
├── skills/                      # skill dạng prompt (markdown)
├── tests/                       # 75 test
├── data/                        # runtime: projects/, mcp-images/, .secret_key
└── xanax.db                     # SQLite, tự tạo — 28 bảng
```

---

## Database — 28 bảng

**File:** `hub/database.py` (schema + migration tự chạy lúc startup)

```
AUTH        users · sessions
NHÂN SỰ     agent_configs · departments · skills
DỰ ÁN       projects · work_items · task_alerts
QUY TRÌNH   workflow_tasks · workflow_runs · workflow_outputs
HỌP         meetings · meeting_messages
HUẤN LUYỆN  training_sessions · training_messages · xanax_notes
ĐÁNH GIÁ    benchmarks · benchmark_results
MODEL       model_pool · model_usage · model_usage_hourly · model_call_log
TƯ LIỆU     knowledge_documents
TÀI SẢN     assets
OPS         ops_history
LEGACY      task_sessions · pipeline_logs
```

Vài điểm dễ sai:
- `agent_configs.model_pool_id` là **INTEGER FK** → `model_pool.id`. Cột `model` (string) chỉ còn để tương thích ngược, được derive tự động khi `list_agent_configs()` JOIN với pool. Đừng lưu model string thủ công.
- `workflow_tasks.agents_json`: `[{"agent_id":1, "order":1, "instructions":"...", "model_pool_id":2}]`
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

Mỗi tin nhắn tới Xanax đều kèm snapshot DB tươi (`_build_live_context()` trong `api/websocket_training.py`): agents, skills, dự án, công việc, quy trình, model pool, và `xanax_notes`. Không cần restart để Xanax biết dữ liệu mới.

---

## Quy trình & Phòng họp

**Ngữ cảnh 3 lớp** khi chạy quy trình: mô tả dự án (brief cố định) → mô tả quy trình → input người dùng. Chỉ lớp cuối đổi mỗi lần chạy.

**Phát hiện lỗi:** `_is_error_output()` bắt `[Error]`, `[Hermes error:`, `[Xanax error:` → đánh dấu run `failed`. Trước đây provider trả lỗi dạng text kèm HTTP 200 thì run vẫn bị đánh dấu "Hoàn thành".

**Trong phòng họp**, chỉ Xanax được kích hoạt quy trình. `_is_workflow_command()` nhận diện câu lệnh chạy quy trình (cố ý bắt rộng) và chặn định tuyến tắt về nhân viên — nếu không, lần gọi thứ hai sẽ bị nhân viên "trả lời lại" bằng kết quả bịa thay vì thật sự chạy. Prompt của nhân viên cũng nói rõ họ không có quyền này.

**Lưu trữ:** mỗi lần chạy được archive ra `data/projects/<dự_án>/<quy_trình>/<yyyymmdd_hhmmss>/` — ảnh ghi thẳng vào đó lúc sinh, text + `run_info.json` ghi thêm khi kết thúc. DB vẫn là nguồn hiển thị chính.

---

## Windows subprocess — quy tắc bắt buộc

`asyncio.create_subprocess_exec` **không hoạt động** dưới uvicorn trên Windows. Mọi subprocess phải đi qua `api/agents/subprocess_util.py` → `stream_proc` (dùng `subprocess.Popen` trong `threading.Thread`). Không có ngoại lệ.

MCP stdio server thì khác — Python MCP SDK tự dùng Windows Job Object (`KILL_ON_JOB_CLOSE`), đã kiểm chứng bằng cách hard-kill tiến trình cha: 0 tiến trình mồ côi. Không cần cơ chế dọn PID thủ công.

---

## Kiểm thử

```powershell
python -m pytest tests/ -q      # 75 passed
```

`tests/test_api.py` có `anon_client` (không đăng nhập) và `client` (tự tạo rồi xoá user tạm) — `TestAuthGuard` kiểm tra đúng cả hai chiều: endpoint bị chặn khi không có phiên, và chạy được khi có.

---

## Checklist trước khi deploy

Đã xong:
- [x] Xác thực toàn bộ `/api/*` và `/ws/*`
- [x] Mã hoá `api_key` / `token` khi lưu, che khi trả về API
- [x] Nén gzip (CSS còn 17%, JS còn 24% kích thước gốc)
- [x] Tách CSS/JS khỏi HTML, nạp `defer`
- [x] 75 test tự động

Còn phải làm:
- [ ] Đặt `HUB_SECRET_KEY` và `HUB_API_KEY` thật (đang là placeholder trong `.env.example`)
- [ ] Đặt `XANAX_SECRET_KEY` cố định, đừng để tự sinh trên server
- [ ] `HUB_DEBUG=false` (đang `true` → uvicorn bật reload)
- [ ] Dockerfile + reverse proxy + TLS
- [ ] Chuyển sang Postgres nếu cần nhiều người dùng đồng thời
- [ ] Hai script CDN (`marked`, `chart.js`) đang tải từ jsdelivr — mất mạng ngoài là mất biểu đồ và render markdown

---

## Gỡ lỗi nhanh

| Triệu chứng | Nguyên nhân thường gặp |
|---|---|
| LLM không phản hồi | Kiểm tra `GET /api/health` và `HUB_LLM_API_BASE` trong `.env` |
| Model Pool báo `404 no active credential` | Credential phải cấu hình ở dashboard của provider (9router), không phải trong Xanax |
| Nhân viên dùng sai model | Nhân sự → chọn agent → đổi Model → Save. `model_pool_id` là số nguyên, không phải chuỗi |
| Sinh ảnh thất bại | Model text không hỗ trợ `/images/generations` — cần thêm image model vào pool. Lỗi hiện nguyên văn kèm tên model và HTTP status |
| Skill MCP không thấy tool nào | Bấm "Kiểm tra kết nối" trên thẻ skill. Sai `target` hoặc sai Python venv là nguyên nhân phổ biến nhất |
| MCP báo `'Server' object has no attribute 'list_tools'` | SDK `mcp` 2.x đã bỏ decorator này. Ghim `mcp<2` |
| Tab URL không load đúng | Tên tab phải có trong `_HUB_TABS` (`hub/server.py`) |
| Preflight CORS bị 401 | Ai đó đảo thứ tự `add_middleware` — AuthGuard phải thêm TRƯỚC CORS |

---

## Quy ước khi sửa code

1. Thêm route mới → đăng ký trong `create_app()` (`hub/server.py`). Middleware tự bảo vệ, không cần thêm `Depends`.
2. Thêm bảng DB mới → thêm vào `init_db()` **và** viết migration trong `database.py`.
3. Cần slug? Dùng `core/slugify.py`. Đừng viết lại bằng JS — bản Python bóc dấu tiếng Việt (`cắt ảnh` → `cat_anh`), bản JS ngây thơ sẽ ra `c_t_nh` và tên tool lệch nhau.
4. Mọi subprocess đi qua `stream_proc`.
5. Codex CLI nhận prompt qua **stdin**, không qua CLI arg.
6. Pipeline chạy bằng `asyncio.create_task` — không block vòng lặp receive của WebSocket.
7. Đường dẫn SOUL.md luôn qua `_soul_path()`, không hardcode.
8. Thêm khoá bí mật mới vào skill config → thêm tên khoá vào `SECRET_CONFIG_KEYS`.
9. Cuối mỗi phiên làm việc: cập nhật README này cho khớp thực tế.

---

## Giấy phép

Dự án cá nhân, chưa công bố giấy phép.

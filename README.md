# Xanax — AI Agent ERP

Xanax là hệ thống quản lý **nhân viên AI như một công ty**: tuyển (tạo agent), giao việc, xếp thành quy trình nhiều bước, họp bàn, nghiệm thu kết quả, và theo dõi chi phí token.

Chạy hoàn toàn trên máy cá nhân (Windows), với **FastAPI + SQLite** ở backend. Giao diện đang được chuyển dần từ vanilla JS sang **React + TypeScript**; đến Giai đoạn 3, trang đăng nhập, Workspace và Taskrunner React chạy song song với toàn bộ giao diện cũ.

```powershell
cd D:\xanax\backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # sửa HUB_SECRET_KEY trước khi dùng thật
python main.py
```

Mặc định: `http://localhost:8000` → đăng nhập → `/hub`. API docs tại `/api/docs`.

Frontend React khi phát triển chạy qua Vite và proxy cùng origin tới backend:

```powershell
# Terminal 1
cd D:\xanax\backend
python main.py

# Terminal 2
cd D:\xanax\frontend
npm install
npm run dev
```

Mở `http://localhost:5173/login`, `/v2/workspace` hoặc `/v2/taskrunner`. Bản build tạm được FastAPI phục vụ tại các route `/v2/*` này sau khi chạy `npm run build`; các route `/login`, `/hub`, `/workspace` và `/taskrunner` cũ vẫn giữ nguyên.

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
| Model Pool | `/hub/model` | Khai báo model, giới hạn dùng/ngày, test kết nối, biểu đồ top 10. Ba kiểu kết nối: qua provider trung gian, qua API chính chủ, hoặc **qua CLI gói thuê bao** |
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
  ├─ target: <python.exe venv rembg> d:\xanax\backend\mcp_servers\image_cut.py
  └─ tools: ["cut_product", "cut_product_batch"]   ← chọn từng tool, không phải all-or-nothing
```

Chi tiết đáng lưu ý:
- **Một thẻ skill chứa nhiều tool.** UI hiện danh sách tool kèm checkbox; bỏ chọn tool nào thì tool đó không được đăng ký.
- **Đổi lựa chọn tool không cần kết nối lại** — chỉ đăng ký lại registry (0.01s thay vì ~7s).
- `tools: []` (bỏ chọn hết) khác với không có khoá `tools` (lấy tất cả). Đây là phân biệt cố ý.
- Kết nối được giữ bền bởi một supervisor task; `mcp_manager.close_all()` chạy khi server tắt.
- Tool trả về ảnh (`ImageContent`) được ghi ra `backend/data/mcp-images/YYYYMMDD/` và trả về đường dẫn file.
- Tiền tố tên tool do backend sinh (`core/slugify.py`, có bóc dấu tiếng Việt) và trả về qua `GET /api/tools/mcp/status` — **frontend không được tự slugify lại**.
- Sau khi dời backend, cập nhật target tuyệt đối trong DB bằng `python tools/migrate_mcp_server_paths.py` để xem trước, rồi thêm `--apply` để backup và ghi.

### MCP server có sẵn: `backend/mcp_servers/image_cut.py`

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

- Khoá lấy từ `XANAX_SECRET_KEY`, không có thì tự sinh vào `backend/data/.secret_key`.
- API trả về giá trị đã che (`••••••••`); khi lưu, giá trị che được merge lại thành giá trị cũ — sửa skill không làm mất token.
- Đây là bảo vệ **dữ liệu khi nằm yên**, không phải bảo vệ quyền truy cập API. Ai qua được `auth_guard` vẫn dùng được skill.
- Di trú dữ liệu cũ: `python tools/encrypt_existing_secrets.py` (mặc định chỉ xem trước, `--apply` để ghi, tự backup DB và kiểm tra giải mã khớp).

### Phiên đăng nhập
TTL 8h · idle timeout 15 phút (client) · purge cron 30 phút · cookie `xanax_session` (HttpOnly, SameSite=strict) · mật khẩu PBKDF2-HMAC-SHA256 260.000 vòng · mọi phiên bị xoá khi server restart.

---

## Cấu trúc thư mục

```
xanax/
├── backend/
│   ├── main.py                  # uvicorn runner + banner + tự mở trình duyệt
│   ├── hub/
│   ├── server.py                # create_app(): routes, middleware, lifespan, static
│   ├── config.py                # Pydantic Settings (env prefix HUB_)
│   ├── database.py              # aiosqlite — toàn bộ DB operations + migration
│   └── events.py                # event bus nội bộ
│   ├── api/
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
│   ├── core/
│   ├── mcp_client.py            # MCP client: stdio/http/sse, chọn tool, ảnh
│   ├── skill_tools.py           # skill type "api" → tool động
│   ├── secret_crypto.py         # AES-256-GCM cho api_key/token
│   ├── model_pool_bridge.py     # gọi model qua pool, LimitExceededError
│   ├── cli_provider.py          # gọi model qua CLI gói thuê bao (claude/codex),
│   │                            # build_clean_env() chặn rò rỉ biến sang gateway
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
│   ├── mcp_servers/
│   ├── image_cut.py             # MCP server cắt ảnh sản phẩm
│   └── xanax_skills.py          # cầu nối MCP: phơi skill api/builtin cho CLI gói
│   ├── dashboard/               # giao diện HTML cũ, giữ tới Giai đoạn 6
│   ├── login.html · index.html · workspace.html · taskrunner.html
│   ├── hub.html                 # khung SPA
│   └── static/
│       ├── hub.css              # ~83 KB — tách khỏi hub.html
│       ├── hub.js               # ~239 KB — tách khỏi hub.html, nạp defer
│       └── images/
│   ├── tools/                   # builtin tools + script bảo trì
│   ├── skills/                  # skill dạng prompt (markdown)
│   ├── tests/                   # test suite
│   ├── data/                    # runtime: projects/, mcp-images/, .secret_key
│   └── xanax.db                 # SQLite, tự tạo — 28 bảng
├── deliverables/
├── docs/
├── frontend/
│   ├── src/                     # React + TypeScript: API client, store, i18n, component, pages
│   ├── package.json
│   ├── vite.config.ts           # proxy /api, /ws và static/trang cũ tới :8000
│   └── dist/                    # bản build có hash, không commit
└── README.md
```

---

## Database — 28 bảng

**File:** `backend/hub/database.py` (schema + migration tự chạy lúc startup)

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

**Lưu trữ:** mỗi lần chạy được archive ra `backend/data/projects/<dự_án>/<quy_trình>/<yyyymmdd_hhmmss>/` — ảnh ghi thẳng vào đó lúc sinh, text + `run_info.json` ghi thêm khi kết thúc. DB vẫn là nguồn hiển thị chính.

---

## Windows subprocess — quy tắc bắt buộc

`asyncio.create_subprocess_exec` **không hoạt động** dưới uvicorn trên Windows. Mọi subprocess phải đi qua `api/agents/subprocess_util.py` → `stream_proc` (dùng `subprocess.Popen` trong `threading.Thread`). Không có ngoại lệ.

MCP stdio server thì khác — Python MCP SDK tự dùng Windows Job Object (`KILL_ON_JOB_CLOSE`), đã kiểm chứng bằng cách hard-kill tiến trình cha: 0 tiến trình mồ côi. Không cần cơ chế dọn PID thủ công.

Prompt phải đi qua **stdin**, không qua `argv`. Prompt của agent dài hàng nghìn ký tự, nhiều dòng, có tiếng Việt và dấu nháy — nhét vào dòng lệnh là hỏng escaping trên Windows.

---

## Gọi model qua CLI gói thuê bao

Nhân viên có thể chạy bằng **tiến trình CLI đã đăng nhập gói** (`claude`, `codex`) thay vì gọi HTTP tới provider trung gian. Không có API key nào trong cấu hình, nên không có key nào để lộ hay bị thu hồi, và chi phí nằm trong gói thuê bao thay vì tính theo token.

Thêm ở **Model Pool → Thêm model → tab "Qua CLI (gói thuê bao)"**:

| Ô | Ý nghĩa |
|---|---|
| Engine | `claude_cli` (gói Claude) hoặc `codex_cli` (gói ChatGPT) |
| Model ID | `claude-haiku-4-5`, `gpt-5.5`… — truyền thành `--model`/`-m` |
| Thư mục tài khoản | `CLAUDE_CONFIG_DIR` / `CODEX_HOME`. Để trống = tài khoản mặc định. **Mỗi tài khoản một thư mục** — đây là cách chạy nhiều gói song song trên một máy, và cách xoay tài khoản khi một gói cạn hạn mức phiên |

Gán model đó cho nhân viên như bình thường (Nhân sự → chọn agent → Model). Phòng họp và Quy trình tự động dùng, vì cả hai đều đi qua `stream_from_agent_models()`. Thứ tự ưu tiên nhiều model vẫn hoạt động: model CLI hết hạn mức phiên thì tự chuyển sang model kế tiếp trong danh sách.

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
python -m pytest tests/ -q      # 311 passed
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
- [ ] Sau Giai đoạn 6: cho loader đọc `XANAX_SECRET_KEY` từ `backend/.env`; hiện khoá đã được ghim ở đó nhưng `core/secret_crypto.py` vẫn chỉ đọc process environment rồi fallback sang `backend/data/.secret_key`
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
| Model CLI báo `model requires a newer version of Codex` | Model mặc định của gói mới hơn `codex` CLI đang cài. Điền Model ID rõ ràng (`gpt-5.5`, `gpt-5.4`) thay vì để trống, hoặc nâng cấp CLI |
| Model CLI báo `not supported when using Codex with a ChatGPT account` | Model đó chỉ dùng được với API key, không dùng được bằng gói. Đổi sang model khác |
| Model CLI bỗng báo lỗi xác thực dù không đổi gì | Kiểm biến rò rỉ: `Get-ChildItem env: \| Where-Object Name -match 'ANTHROPIC\|OPENAI'`. `build_clean_env()` chặn chúng khi spawn, nhưng nếu ai đó gọi `stream_proc` mà quên truyền `env` thì lỗ hổng quay lại |
| Model CLI hết hạn mức phiên 5 giờ | Xoay tài khoản: đổi ô "Thư mục tài khoản" của entry sang thư mục gói khác. Không cần restart |
| Nhân viên báo "đã đăng/đã gửi" nhưng thực tế không có gì | Không còn xảy ra âm thầm: bước sẽ trượt kèm lý do. Nếu vẫn gặp, kiểm `collect_tool_invocations()` có ghi gì không |
| Bước trượt vì `KHÔNG gọi công cụ` dù nhân viên đã giao đủ việc | Kỹ năng đó có phải loại `api` không? Chỉ `api` mới bắt buộc. Nếu là `mcp`/`builtin` mà vẫn trượt thì là lỗi — xem `_required_tool_names()` |
| `Nhân viên này có kỹ năng cần gọi công cụ...` | Nhân viên chỉ còn model không gọi được công cụ. Với `claude_cli` thì phải có `skill_ids`; với `codex_cli` thì chưa hỗ trợ — thêm 1 model OpenAI-compatible |
| MCP server báo `status: pending`, tool không hiện | Server khởi động quá chậm (thường do MCP lồng MCP), hoặc `ToolSearch` bị tắt nên model không nạp được schema |
| Nhân viên CLI kể việc sắp làm thay vì làm | `claude`/`codex` là agent lập trình, phản xạ là báo kế hoạch trước. Đã chặn bằng `_DELIVERABLE_ONLY` + `--permission-mode default` (KHÔNG dùng `plan`) |
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

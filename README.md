# Xanax — Multi-Agent AI Hub

Xanax là một web UI cá nhân cho AI agent, chạy trên **Windows**, viết bằng **FastAPI + vanilla JS**. Backend giao tiếp với một LLM endpoint tuỳ chỉnh (OpenAI-compatible). Hệ thống có **5 module chính**: Chat, Training, Quy Trình (Workflow), Hub (Agent/Project/Meeting/Benchmark), và Model Pool.

> **Đọc README này trước** khi mở bất kỳ file nào. Đây là tài liệu chính thức phản ánh đúng trạng thái hiện tại của project.

---

## Tiến độ tổng quan (cập nhật 2026-06-30)

| Module | Trạng thái | Ghi chú |
|--------|-----------|---------|
| Chat (`/ws/chat`) | ✅ Hoàn chỉnh | Streaming, in-memory session |
| Training (`/workspace`) | ✅ Hoàn chỉnh | Live DB context inject, tool use, persistent notes |
| Quy Trình (`/taskrunner`) | ✅ Hoàn chỉnh | Multi-agent pipeline, error detection, image gen với fallback |
| Hub Dashboard (`/hub`) | ✅ Hoàn chỉnh | Home, Nhân Sự, Kỹ Năng, Dự Án, Họp, Đánh Giá, Mô Hình |
| Model Pool (`/hub/model`) | ✅ Hoàn chỉnh | Pool API qua 9router, giới hạn usage, biểu đồ top 10 nằm ngang, realtime limit preview |
| Hermes Agent Framework | ✅ Cơ bản | ReAct loop, planner, memory, tool registry |
| Orchestrator & Scheduler | ✅ Có sẵn | Chưa có UI riêng — chạy ngầm |
| Agent–Task Matcher | ✅ Hoàn chỉnh | Keyword scoring, alert khi không match |
| Xanax Live Context | ✅ MỚI | Inject DB snapshot vào mọi chat message — agents/skills/projects/model pool |
| Xanax Tool Use | ✅ MỚI | Xanax tạo work item, update, trigger workflow, save/delete note |

**Điều chưa làm / có thể mở rộng tiếp:**
- UI quản lý Orchestrator/Scheduler (hiện chỉ có API)
- Persistent chat history (hiện in-memory, mất khi restart)
- Multi-user support (hiện 1 admin account)
- Real-time notification cho task alerts
- Export kết quả workflow ra PDF/markdown
- Real-time fanpage monitoring (cần tích hợp Facebook API)
- Image generation: cần thêm model image vào Model Pool (DALL-E / Flux / SD) — text model không generate image

---

## Cấu trúc thư mục

```
xanax/
├── main.py                          # Entrypoint: uvicorn runner + banner
├── hub/
│   ├── server.py                    # App factory, tất cả routes, lifespan, static
│   ├── config.py                    # Pydantic Settings (env prefix: HUB_)
│   ├── database.py                  # aiosqlite: toàn bộ DB operations
│   └── events.py                    # Internal async event bus
├── core/
│   ├── hermes_bridge.py             # LLM client + in-memory chat sessions
│   ├── model_pool_bridge.py         # OpenAI-compatible caller cho Model Pool
│   │                                #   stream_from_pool(model_pool_id, messages)
│   │                                #   test_model_connection(model_pool_id)
│   │                                #   LimitExceededError khi vượt giới hạn
│   ├── image_gen.py                 # ★ CẬP NHẬT: ImageGenError exception, lỗi cụ thể
│   │                                #   generate_image() raises ImageGenError thay vì return None
│   ├── soul_sync.py                 # Sync SOUL.md (startup) + append feedback
│   ├── orchestrator.py              # Background multi-agent orchestrator
│   ├── scheduler.py                 # APScheduler: cron/delayed/queue jobs
│   ├── matcher.py                   # Smart keyword matcher agent↔task
│   └── hermes/                      # Internal agent framework
│       ├── agent.py                 # HermesAgent (ReAct loop)
│       ├── context.py               # AgentContext, AgentStatus
│       ├── memory.py                # AgentMemory (in-memory + TTL)
│       ├── planner.py               # HermesPlanner (task decomposition)
│       └── tool_registry.py         # ToolRegistry: register/call tools
├── api/
│   ├── websocket.py                 # /ws/chat
│   ├── websocket_training.py        # ★ CẬP NHẬT: /ws/training
│   │                                #   _build_live_context() — inject DB snapshot real-time
│   │                                #   _parse_tool_calls() / _execute_tool_call()
│   │                                #   Xanax tool use: [[XANAX:action|param=value]]
│   ├── websocket_workflow.py        # ★ CẬP NHẬT: /ws/workflow
│   │                                #   _is_error_output(): detect [Error] từ provider
│   │                                #   Model tạo ảnh: lấy từ model_pool_ids của nhân viên
│   │                                #   ImageGenError: lỗi cụ thể thay vì generic message
│   │                                #   _RunSession: chạy ngầm, đóng tab không dừng run
│   ├── websocket_meeting.py         # /ws/meeting
│   ├── websocket_benchmark.py       # /ws/benchmark
│   ├── agents/
│   │   ├── subprocess_util.py       # Thread-based subprocess (Windows-safe)
│   │   ├── claude_runner.py         # Claude CLI wrapper (stream-json)
│   │   └── codex_runner.py          # Codex CLI wrapper (--json, stdin prompt)
│   └── routes/
│       ├── auth.py
│       ├── chat.py
│       ├── health.py
│       ├── agent_configs.py         # ★ CẬP NHẬT: model_pool_id field (int) thay vì model string
│       ├── skills_mgmt.py
│       ├── projects.py
│       ├── meetings.py
│       ├── benchmarks.py
│       ├── task_sessions.py
│       ├── tasks.py
│       ├── tools.py
│       ├── training.py
│       ├── workflow.py
│       └── model_pool.py
├── dashboard/
│   ├── login.html
│   ├── index.html
│   ├── hub.html                     # ★ CẬP NHẬT: agent dùng model_pool_id, limit bars realtime
│   ├── workspace.html               # ★ CẬP NHẬT: handle tool_executed event, tool result bubble
│   ├── taskrunner.html              # ★ CẬP NHẬT: pass/fail button fix, cancel fix, badge fix
│   └── static/
│       └── generated/               # Ảnh do image gen tạo ra (tự động tạo)
├── xanax.db                         # SQLite (auto-created)
├── .env
├── .env.example
├── pyproject.toml
└── requirements.txt
```

---

## Khởi động

```powershell
cd D:\xanax
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

Server mặc định: `http://localhost:8000`

---

## Pages & Routes đầy đủ

| URL | File | Mô tả |
|-----|------|--------|
| `/` hoặc `/login` | `login.html` | Đăng nhập |
| `/hub` | `hub.html` | Hub chính |
| `/hub/{tab}` | `hub.html` | agents / skills / tasks / meeting / benchmark / train / runner / model / settings |
| `/workspace` | `workspace.html` | Training UI (Xanax chat) |
| `/taskrunner` | `taskrunner.html` | Quy Trình UI |
| `/taskrunner?embed=1` | `taskrunner.html` | Embed mode trong iframe |
| `/api/docs` | — | Swagger UI |
| `/api/health` | — | Health check |
| `/api/agent-configs/` | — | Agent persona CRUD |
| `/api/skills/` | — | Skill/tool CRUD |
| `/api/projects/` | — | Project + work item CRUD + matcher |
| `/api/meetings/` | — | Meeting CRUD |
| `/api/benchmarks/` | — | Benchmark CRUD + results |
| `/api/workflow/tasks` | — | Workflow task CRUD |
| `/api/workflow/runs` | — | Workflow run history |
| `/api/workflow/outputs/{id}` | — | PATCH output (pass/fail, notes) |
| `/api/model-pool` | — | Model Pool CRUD |
| `/api/model-pool/stats` | — | Top 10 models usage chart |
| `/api/model-pool/{id}/test` | — | Test kết nối model |
| `/ws/chat` | `api/websocket.py` | WebSocket chat |
| `/ws/training` | `api/websocket_training.py` | WebSocket training |
| `/ws/workflow` | `api/websocket_workflow.py` | WebSocket workflow runner (actions: `run`, `attach`, `list_active`, `cancel`) |
| `/ws/meeting` | `api/websocket_meeting.py` | WebSocket meeting room |
| `/ws/benchmark` | `api/websocket_benchmark.py` | WebSocket benchmark runner |

---

## Database Schema (đầy đủ — 19 bảng)

**File:** `hub/database.py` | **Path:** `D:\xanax\xanax.db`

```sql
-- === AUTH ===
users(id, username, password_hash, created_at)
sessions(token, user_id, expires_at)

-- === TRAINING ===
training_sessions(id, title, task_description, status, result_notes, created_at, updated_at)
training_messages(id, session_id, role, content, created_at)

-- === XANAX MEMORY ★ MỚI ===
xanax_notes(id, content, created_at)
  -- Ghi nhớ bền vững của Xanax qua các session
  -- Xanax ghi bằng [[XANAX:save_note|content=...]]
  -- Được inject vào live context mỗi chat message

-- === WORKFLOWS ===
workflow_tasks(id, name, description, project_id, agents_json, schedule_enabled, schedule_cron, status, created_at, updated_at)
-- agents_json: [{"agent_id":1, "agent_name":"...", "order":1, "instructions":"...", "model_pool_id":2}]

workflow_runs(id, task_id, project_id, task_name, status, triggered_by, started_at, completed_at, created_at)
-- status: 'pending'|'running'|'completed'|'failed'|'cancelled'

workflow_outputs(id, run_id, task_id, agent_id, agent_name, step_order, output_content, status, pass_fail, edited_content, notes, created_at)
-- status: 'done'|'error'  (error khi agent stream [Error]... hoặc image gen fail)
-- pass_fail: null|'pass'|'fail'

-- === HUB: AGENT CONFIGS ===
agent_configs(id, name, role, model, model_pool_id, system_prompt, avatar_color, skills_json, enabled, created_at, updated_at)
  -- model_pool_id ★ MỚI: INTEGER FK → model_pool.id
  -- Khi set model_pool_id, workflow dùng đúng pool entry đó
  -- model (string) vẫn còn cho backward compat, được derive từ pool khi list_agent_configs()

skills(id, name, description, type, config_json, enabled, created_at)
  -- skill không cấu hình model riêng: model luôn lấy từ nhân viên được gán

-- === HUB: PROJECTS & KANBAN ===
projects(id, name, description, status, created_at, updated_at)
work_items(id, project_id, title, description, status, priority, assigned_agent_id, match_score, match_reason, created_at, updated_at)
task_alerts(id, work_item_id, project_id, title, reason, status, suggestions_json, created_at, resolved_at)

-- === HUB: MEETINGS ===
meetings(id, title, topic, status, participants_json, created_at, ended_at)
meeting_messages(id, meeting_id, sender, sender_type, content, created_at)

-- === HUB: BENCHMARKS ===
benchmarks(id, name, role_description, test_cases_json, models_json, status, created_at, completed_at)
benchmark_results(id, benchmark_id, model, scores_json, responses_json, recommendation, created_at)

-- === MODEL POOL ===
model_pool(id, name, provider, model_id, base_url, api_key, category, max_requests_per_day, max_tokens_per_day, enabled, created_at)

model_usage(id, model_pool_id, date, request_count, tokens_input, tokens_output)
  -- UNIQUE(model_pool_id, date)

-- === TASK RUNNER (legacy) ===
task_sessions(...)
pipeline_logs(...)
```

---

## Module: Xanax Training — Live Context & Tool Use ★ MỚI

**File:** `api/websocket_training.py`

### Live Context Injection

Mỗi chat message gửi tới Xanax đều kèm snapshot DB mới nhất:

```
System prompt = SOUL.md  +  _build_live_context()
```

`_build_live_context()` query DB tươi mỗi lần, gồm:
- Danh sách agents (enabled/disabled, model, skills)
- Danh sách skills
- Dự án + trạng thái
- Công việc (work items) của từng dự án
- Quy trình (workflow tasks)
- Model pool đầy đủ
- **xanax_notes** (ghi nhớ bền vững của Xanax)

### Xanax Tool Use

Xanax có thể thực hiện hành động bằng cú pháp nhúng trong response:

```
[[XANAX:action|param1=value1|param2=value2]]
```

Server parse sau khi stream xong → thực thi → gửi `tool_executed` event về client.

**Hành động hỗ trợ:**

| Action | Params | Mô tả |
|--------|--------|--------|
| `save_note` | `content=...` | Lưu ghi nhớ vào `xanax_notes` |
| `delete_note` | `id=N` | Xóa note theo ID |
| `create_work_item` | `project_id=N\|title=...\|description=...\|priority=...\|assignee=...` | Tạo công việc mới |
| `update_work_item` | `id=N\|status=...\|priority=...\|assignee=...` | Cập nhật công việc |
| `trigger_workflow` | `task_id=N` | Kích hoạt quy trình |

**Quy tắc:** Xanax chỉ dùng khi Papa yêu cầu hành động cụ thể. Tool calls được strip khỏi response hiển thị (client chỉ thấy kết quả thực thi qua bubble ⚡).

**WebSocket event mới:**
```json
{"type": "tool_executed", "clean_text": "...", "results": [
  {"ok": true, "action": "create_work_item", "message": "Đã tạo công việc #5: \"Design logo\""}
]}
```

---

## Module: Quy Trình — Workflows

**Files:** `dashboard/taskrunner.html`, `api/websocket_workflow.py`, `api/routes/workflow.py`

### Error Detection ★ MỚI

Sau khi stream xong, detect lỗi từ provider:

```python
_STREAM_ERROR_PREFIXES = ("[Error]", "[Hermes error:", "[Xanax error:")

def _is_error_output(text: str) -> bool:
    return any(text.strip().startswith(p) for p in _STREAM_ERROR_PREFIXES)
```

Nếu detect → mark output `error`, run `failed`, gửi `agent_error` event. Không còn mark `completed` sai khi provider trả lỗi dạng text.

### Image Generation ★ CẬP NHẬT

**`core/image_gen.py` — ImageGenError:**

```python
class ImageGenError(Exception): pass

async def generate_image(...) -> str:
    # Raises ImageGenError với message cụ thể thay vì return None
    # HTTP error → "HTTP 404 từ image model: ..."
    # Timeout → "Timeout sau 120s — model 'X' không phản hồi"
    # No data → "Model không trả về ảnh. Response: ..."
```

**Model dùng để tạo ảnh:** lấy đúng danh sách model đã gán cho nhân viên (`model_pool_ids`, tab Nhân sự), theo thứ tự ưu tiên; model nào bị xoá/tắt thì bỏ qua và dùng model kế tiếp. Không có model riêng cho skill và không phân loại text/ảnh.

Lỗi hiển thị cụ thể: `❌ Tạo ảnh thất bại [GPT-4o · openai/gpt-4o]: HTTP 404 từ image model: ...`

> **Lưu ý:** Model được gán cho nhân viên phải hỗ trợ `/images/generations`, nếu không provider sẽ trả lỗi và lỗi đó hiện nguyên văn ngay.

### UI Fixes (taskrunner.html)

- **Cancel button:** `endRun(finalStatus)` nhận final status, patch badge ngay lập tức trước khi DB load
- **`S.cancelling = false`** được reset đúng trong `endRun()` — không còn stuck "Đang huỷ..."
- **Duplicate "Đang huỷ...":** Đã xóa `setHTML('mon-status', ...)` thừa trong `cancelRun()`
- **Pass/fail buttons:** CSS `:not([disabled]):hover` — disabled không còn hover effect; non-selected button ẩn sau khi verdict
- **`data-run-id`** attribute trên run cards để patch badge bằng DOM thay vì reload

---

## Module: Model Pool (`/hub/model`) ★ CẬP NHẬT

### Biểu đồ Top 10 nằm ngang

CSS class `mp-chart` đổi từ vertical bar chart sang **horizontal bar chart**:
- Y axis: tên model (bên trái, width 130px)
- X axis: số lần sử dụng (bar chạy sang phải)
- Số hiển thị ở đầu bar bên phải

### Limit Bars Realtime Preview

Khi mở modal Sửa model và gõ vào "Giới hạn request/ngày" hoặc "Giới hạn token/ngày":
- `oninput="livePreviewLimits()"` → cập nhật bars ngay lập tức
- Dùng `_mpUsageToday` (lưu khi select model) làm usage hiện tại
- `_renderLimitBars(maxReq, maxTok)` là function dùng chung cho cả select lẫn live preview

---

## Module: Tab Nhân Sự — Agent Model Pool Link ★ CẬP NHẬT

**Thay đổi kiến trúc:**

Trước: `agent.model` = string như `"cx/gpt-5.4"` → workflow tìm `model_pool_id` luôn ra `None`

Sau: `agent.model_pool_id` = integer ID trong `model_pool` table

**Dropdown "Model"** trong form agent:
- `opt.value = m.id` (numeric pool ID)
- `opt.textContent = m.name (m.model_id)` (hiển thị)
- Load: `populateAgentModelSelect(a.model_pool_id || '')`

**`saveAgent()` gửi:**
```javascript
{ model_pool_id: parseInt(poolIdStr) || null, ... }
```

**`list_agent_configs()`** JOIN với `model_pool` để derive `model` string khi `model_pool_id` set:
```sql
SELECT a.*, mp.model_id AS pool_model_id
FROM agent_configs a
LEFT JOIN model_pool mp ON mp.id = a.model_pool_id
```

**DB migration** (tự động khi server start):
```sql
ALTER TABLE agent_configs ADD COLUMN model_pool_id INTEGER
```

**Quy tắc khi cập nhật agent model:** Sau khi thêm model mới vào pool, vào tab Nhân Sự → chọn agent → dropdown Model → chọn model mới → Save. `model_pool_id` sẽ được cập nhật đúng.

---

## Hub Dashboard (`/hub`) — Cấu trúc

### URL Routing theo tab

```
/hub              → Home tab
/hub/agents       → Nhân Sự
/hub/skills       → Kỹ Năng
/hub/tasks        → Dự Án
/hub/meeting      → Họp
/hub/benchmark    → Đánh Giá
/hub/train        → Huấn Luyện
/hub/runner       → Quy Trình (embed taskrunner.html)
/hub/model        → Mô Hình (Model Pool)
/hub/settings     → Cài Đặt
```

### DB Sync giữa Tab Quy Trình và Tab Dự Án

`switchTab()` trong hub.html: khi switch về tab `tasks` mà đang ở `results` sub-tab → tự động gọi `loadProjectResults()` để sync pass/fail từ taskrunner.

---

## Xanax Training — WebSocket Protocol

**Client → Server:**
```json
{"training_session_id": 1, "message": "..."}
{"action": "summarise_pass", "session_id": 1}
{"action": "summarise_fail", "session_id": 1}
{"action": "improve_from_fail", "session_id": 1, "feedback": "..."}
```

**Server → Client:**
```json
{"type": "status",           "status": "thinking"}
{"type": "chunk",            "content": "..."}
{"type": "tool_executed",    "clean_text": "...", "results": [...]}
{"type": "done"}
{"type": "notes_updated",    "content": "<summary>"}
{"type": "failure_analysed", "content": "<analysis>"}
{"type": "error",            "message": "..."}
```

---

## LLM Backend

```env
HUB_LLM_API_BASE=http://localhost:11434
HUB_LLM_MODEL=hermes3
HUB_LLM_API_KEY=
```

**Hermes Bridge** — Chat, Training, Meeting, Benchmark, Workflow (fallback):
```python
hermes.chat_stream(session_id, message)
hermes.stream_with_context(messages)
hermes.complete_with_context(messages) -> str
```

**Model Pool Bridge** — Workflow khi agent có `model_pool_id`:
```python
stream_from_pool(model_pool_id, messages)
test_model_connection(model_pool_id)
```

---

## Bảo mật phiên

- TTL: 8h | Idle timeout (client): 15 phút | Purge cron: 30 phút
- Tất cả sessions xóa khi server restart
- Cookie: `xanax_session` (HttpOnly, SameSite=strict)
- Password: PBKDF2-HMAC-SHA256, 260,000 iterations

---

## Design & UI

- **Font:** Space Grotesk + JetBrains Mono
- **Background:** `#06080f` | **Accent:** `#00d9f5` (cyan) + `#9366ff` (purple)
- **Status:** `#22c55e` (green) / `#ef4444` (red) / `#f59e0b` (amber) / `#3b82f6` (blue)
- **Tool result bubble:** avatar `⚡`, màu tím `rgba(139,92,246,...)`

---

## Debugging Checklist

**LLM không phản hồi:**
- Kiểm tra `GET /api/health` và `.env` config

**Model Pool lỗi "404 no active credential":**
- Cấu hình provider credentials trong 9router dashboard, không phải trong Xanax
- API key Xanax = API key 9router

**Workflow agent dùng sai model / image gen dùng pool cũ:**
- Vào Nhân Sự → chọn agent → đổi Model → Save
- `model_pool_id` giờ là integer ID, không phải string
- Tạo ảnh cũng dùng chính model của nhân viên đó — không cần cấu hình gì thêm ở skill

**Image generation thất bại:**
- Lỗi sẽ hiển thị cụ thể: tên model, HTTP status, message từ API
- Text model KHÔNG hỗ trợ `/images/generations` → cần thêm image model riêng vào pool
- Fallback tự động: skill config → agent pool → bất kỳ pool enabled nào

**Workflow bị "Hoàn thành" sai:**
- Provider trả `[Error] ...` với HTTP 200 → `_is_error_output()` detect và mark `failed`
- Image gen fail không còn mark `completed`

**Xanax không biết dữ liệu công ty:**
- Live context được inject mỗi message — không cần restart
- Nếu Xanax không nhớ giữa session: dùng `[[XANAX:save_note|content=...]]` để lưu vào DB

**Hub: tab URL không load đúng:**
- `_HUB_TABS` trong `hub/server.py` phải chứa tên tab

**Workflow agents không hiện trong picker:**
- `S.agents = (d.agents || []).filter(a => a.enabled !== 0)`

---

## Windows Subprocess (QUAN TRỌNG)

**Vấn đề:** `asyncio.create_subprocess_exec` không hoạt động trên Windows uvicorn.

**Giải pháp:** `api/agents/subprocess_util.py` — `subprocess.Popen` trong `threading.Thread`.

> **Quy tắc bắt buộc:** Mọi subprocess phải qua `stream_proc`. Không dùng `asyncio.create_subprocess_exec`.

---

## Notes bắt buộc cho mọi session mới

> [!IMPORTANT]
> **Rule 0 — BẮT BUỘC:** Cuối mỗi phiên làm việc, **phải cập nhật README.md** để phản ánh đúng những gì đã thay đổi.

1. **`subprocess_util.py`** là bắt buộc cho mọi subprocess — không bypass.
2. **Codex** luôn nhận prompt qua stdin, không qua CLI arg.
3. **Pipeline** chạy bằng `asyncio.create_task` — không block WS receive loop.
4. **Training** auto-summarise chạy background — không block response.
5. **SOUL.md path** luôn dùng `_soul_path()` function, không hardcode.
6. Session TTL = 8h, idle timeout = 15 phút (client-side), purge cron = 30 phút.
7. Khi thêm route mới: đăng ký trong `hub/server.py` → `create_app()`.
8. Khi thêm bảng DB mới: thêm vào `init_db()` + migration trong `database.py`.
9. **`agent.model_pool_id`** = integer FK → `model_pool.id`. `agent.model` string được derive tự động khi list. Không lưu model string thủ công nữa.
10. **`xanax_notes`** table: Xanax ghi bằng tool use, được inject vào live context. CRUD: `create_xanax_note`, `list_xanax_notes`, `delete_xanax_note`.
11. **Xanax tool use** format: `[[XANAX:action|param=value]]` cuối response. Server strip trước khi lưu vào `training_messages`. Client nhận `tool_executed` event riêng.
12. **`_build_live_context()`** trong `websocket_training.py`: query DB tươi mỗi chat message. Bao gồm cả `xanax_notes`.
13. **`_is_error_output()`** trong `websocket_workflow.py`: detect `[Error]`, `[Hermes error:]`, `[Xanax error:]` → mark run `failed`.
14. **`generate_image()`** raises `ImageGenError` (không return None). Workflow catch và hiển thị lỗi cụ thể.
15. **Model tạo ảnh**: dùng `model_pool_ids` của nhân viên theo thứ tự ưu tiên, bỏ qua entry đã xoá/tắt. Không có config riêng theo skill.
16. **`update_agent_config`** allowed fields: thêm `model_pool_id`. Cho phép set về `None` (khác các field khác không được None).
17. **`patch_agent`** route dùng `body.model_dump(exclude_unset=True)` — chỉ update field được gửi, cho phép `model_pool_id=null`.
18. **Model Pool chart**: nằm ngang (horizontal), Y=tên model, X=request count. CSS class `mp-bar-track` wrap bar.
19. **Limit bars realtime**: `_renderLimitBars(maxReq, maxTok)` + `_mpUsageToday` global. `livePreviewLimits()` gọi từ `oninput`.
20. **Workflow 3-layer context**: project brief → task description → user_input. Chỉ user_input thay đổi mỗi lần chạy.
21. **Project description** = brief cố định, inject tự động vào mọi workflow run thuộc dự án.
22. **Workflow scheduler**: `restore_schedules()` trong `api/routes/workflow.py` load lại khi startup.

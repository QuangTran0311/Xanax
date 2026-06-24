# Xanax

> [Tiếng Việt](#tiếng-việt) | [English](#english)

## Tiếng Việt

Xanax là hub server điều phối AI, được xây dựng trên lõi agent Hermes. Hệ thống cung cấp một backend thống nhất cho hội thoại có xác thực, tri thức dài hạn của agent, đánh giá và định tuyến model, quy trình họp đa tác tử, cùng tích hợp MCP.

### Chức năng chính

- Phiên hội thoại sử dụng Hermes agent và các model Anthropic.
- Tri thức SOUL bền vững và bộ nhớ theo episode để duy trì ngữ cảnh agent.
- Registry model, theo dõi mức sử dụng và chọn model dựa trên điểm hiệu năng.
- Phòng họp hỗ trợ cộng tác có cấu trúc giữa các agent chuyên biệt.
- Xác thực JWT và tạo tài khoản quản trị ban đầu khi khởi động.
- Công cụ MCP cho session, dữ liệu SOUL, bộ nhớ, telemetry model và cuộc họp.
- PostgreSQL có hỗ trợ pgvector.

### Kiến trúc

```text
Client / MCP host
       |
       +--> FastAPI API (app/)
       |      |
       |      +--> Lõi agent Hermes
       |      +--> Xác thực, session, SOUL, họp, dịch vụ model
       |      +--> PostgreSQL + pgvector
       |
       +--> MCP server (mcp_server/)
```

Ứng dụng Python/FastAPI là runtime chính. Thư mục `src/` chứa một bản triển khai TypeScript và các công cụ hỗ trợ được giữ song song với dịch vụ Python.

### Yêu cầu

- Python 3.11 trở lên
- Docker và Docker Compose
- Anthropic API key

Node.js 20.19 trở lên chỉ cần thiết khi dùng tooling TypeScript trong `src/`.

### Khởi chạy nhanh

1. Tạo và kích hoạt môi trường ảo Python.

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Cài đặt dependency Python.

   ```powershell
   pip install -e .
   ```

3. Tạo cấu hình cục bộ từ file mẫu và thay bằng giá trị bảo mật.

   ```powershell
   Copy-Item .env.example .env
   ```

   Tối thiểu cần cấu hình `ANTHROPIC_API_KEY`, `JWT_SECRET`, `JWT_REFRESH_SECRET` và các biến `ADMIN_*` ban đầu.

4. Khởi động PostgreSQL có pgvector.

   ```powershell
   docker compose -f docker/docker-compose.yml up -d
   ```

5. Chạy migration cơ sở dữ liệu.

   ```powershell
   alembic upgrade head
   ```

6. Khởi động API server.

   ```powershell
   python run.py
   ```

Service mặc định chạy tại `http://localhost:3000`. Khi đặt `NODE_ENV=development`, tài liệu OpenAPI có tại `http://localhost:3000/docs` và health check tại `http://localhost:3000/health`.

### Cấu hình

Không commit `.env`. Dùng [`.env.example`](.env.example) làm file cấu hình mẫu.

| Biến | Mục đích |
| --- | --- |
| `PORT` | Cổng HTTP server, mặc định là `3000`. |
| `NODE_ENV` | Đặt là `development` để bật API docs và reload. |
| `DATABASE_URL` | Chuỗi kết nối PostgreSQL. |
| `ANTHROPIC_API_KEY` | API key Anthropic dùng cho Hermes chat agent. |
| `HERMES_MODEL` | ID model Anthropic, mặc định `claude-sonnet-4-6`. |
| `JWT_SECRET` | Secret ký access token. |
| `JWT_REFRESH_SECRET` | Secret ký refresh token. |
| `ADMIN_USERNAME` | Tên tài khoản được tạo khi service khởi động. |
| `ADMIN_PASSWORD` | Mật khẩu tài khoản quản trị ban đầu. |
| `WORKSPACE_PATH` | Thư mục gốc mà Workspace API được phép truy cập. |

Hãy tạo các giá trị ngẫu nhiên dài và khác nhau cho hai JWT secret trước khi triển khai.

### API

| Nhóm | Base path | Chức năng |
| --- | --- | --- |
| Xác thực | `/api/auth` | Đăng ký, đăng nhập, refresh token và đăng xuất. |
| Session | `/api/sessions` | Tạo, lấy và đóng phiên hội thoại. |
| Tin nhắn | `/api/messages` | Liệt kê tin nhắn và gửi prompt chat đến Hermes. |
| SOUL | `/api/soul` | Đọc và cập nhật tri thức dài hạn của agent. |
| Model | `/api/models` | Kiểm tra model, lịch sử điểm số và telemetry sử dụng. |
| Cuộc họp | `/api/meetings` | Mở/đóng cuộc họp, ghi lượt trao đổi và tạo báo cáo. |
| Workspace | `/workspace` | Lấy metadata workspace. |

Xác thực API bằng Bearer token nhận từ `/api/auth/login`.

### MCP Server

Chạy MCP server qua standard input/output:

```powershell
python -m mcp_server.server
```

MCP server cung cấp các tool tạo/kết thúc session, quản lý SOUL, truy cập episodic memory, ghi nhận mức sử dụng model, xem điểm model và quản lý phòng họp.

### Tooling TypeScript

Repository cũng có bản triển khai TypeScript và Prisma schema.

```powershell
npm install
npm run build
npm run dev
```

Các lệnh database hữu ích cho stack TypeScript:

```powershell
npm run db:up
npm run db:generate
npm run db:migrate
npm run db:seed
```

### Cấu trúc dự án

```text
app/            Ứng dụng FastAPI, lõi agent, service, route và model cơ sở dữ liệu
mcp_server/     Model Context Protocol server
migrations/     Alembic migration
prisma/         Prisma schema và migration cho TypeScript stack
soul/           Đặc tả danh tính và hành vi agent
src/            Bản triển khai TypeScript và tooling
docker/          Môi trường PostgreSQL/pgvector cục bộ
```

### Bảo mật

- Chỉ lưu API key, database credential và JWT secret trong `.env`.
- Thay toàn bộ credential mẫu trước khi dùng service ngoài môi trường local.
- Hạn chế CORS origin và bảo vệ đường dẫn workspace trước khi public server.

### Giấy phép

Repository hiện chưa khai báo giấy phép.

---

## English

Xanax is an AI orchestration hub server built around the Hermes agent core. It provides a single backend for authenticated conversations, long-term agent knowledge, model evaluation and routing, multi-agent meeting workflows, and MCP integration.

## Capabilities

- Chat sessions backed by the Hermes agent and Anthropic models.
- Persistent SOUL knowledge and episodic memory for agent context.
- Model registry, usage tracking, and score-based model selection.
- Meeting rooms for structured collaboration between specialist agents.
- JWT authentication with an initial administrator bootstrap account.
- MCP tools for sessions, SOUL data, memory, model telemetry, and meetings.
- PostgreSQL with pgvector support.

## Architecture

```text
Client / MCP host
       |
       +--> FastAPI API (app/)
       |      |
       |      +--> Hermes agent core
       |      +--> Auth, sessions, SOUL, meetings, model services
       |      +--> PostgreSQL + pgvector
       |
       +--> MCP server (mcp_server/)
```

The Python/FastAPI application is the primary runtime. The `src/` directory contains a TypeScript implementation and supporting tooling retained alongside the Python service.

## Requirements

- Python 3.11 or newer
- Docker and Docker Compose
- An Anthropic API key

Node.js 20.19 or newer is only required for the TypeScript tooling in `src/`.

## Quick Start

1. Create and activate a Python virtual environment.

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install the Python dependencies.

   ```powershell
   pip install -e .
   ```

3. Create local configuration from the example file and set secure values.

   ```powershell
   Copy-Item .env.example .env
   ```

   At minimum, configure `ANTHROPIC_API_KEY`, `JWT_SECRET`, `JWT_REFRESH_SECRET`, and the initial `ADMIN_*` values.

4. Start PostgreSQL with pgvector.

   ```powershell
   docker compose -f docker/docker-compose.yml up -d
   ```

5. Apply database migrations.

   ```powershell
   alembic upgrade head
   ```

6. Start the API server.

   ```powershell
   python run.py
   ```

The service listens on `http://localhost:3000` by default. With `NODE_ENV=development`, the OpenAPI documentation is available at `http://localhost:3000/docs` and the health check is at `http://localhost:3000/health`.

## Configuration

Do not commit `.env`. Use [`.env.example`](.env.example) as the configuration template.

| Variable | Purpose |
| --- | --- |
| `PORT` | HTTP server port. Defaults to `3000`. |
| `NODE_ENV` | Set to `development` to enable API documentation and reload. |
| `DATABASE_URL` | PostgreSQL connection string. |
| `ANTHROPIC_API_KEY` | Anthropic API key used by the Hermes chat agent. |
| `HERMES_MODEL` | Anthropic model ID. Defaults to `claude-sonnet-4-6`. |
| `JWT_SECRET` | Secret used to sign access tokens. |
| `JWT_REFRESH_SECRET` | Secret used to sign refresh tokens. |
| `ADMIN_USERNAME` | Username for the account created at startup. |
| `ADMIN_PASSWORD` | Password for the initial administrator account. |
| `WORKSPACE_PATH` | Root directory exposed by the workspace API. |

Generate distinct, long random values for the JWT secrets before deploying.

## API Surface

| Area | Base path | Purpose |
| --- | --- | --- |
| Authentication | `/api/auth` | Register, login, refresh, and logout. |
| Sessions | `/api/sessions` | Create, retrieve, and close conversation sessions. |
| Messages | `/api/messages` | List messages and send chat prompts to Hermes. |
| SOUL | `/api/soul` | Read and update persistent agent knowledge. |
| Models | `/api/models` | Inspect models, score history, and usage telemetry. |
| Meetings | `/api/meetings` | Open/close meetings, capture turns, and generate reports. |
| Workspace | `/workspace` | Retrieve workspace metadata. |

Authenticate with a Bearer token received from `/api/auth/login`.

## MCP Server

Run the MCP server over standard input/output:

```powershell
python -m mcp_server.server
```

The MCP server exposes tools to create and end sessions, manage SOUL knowledge, access episodic memory, record model usage, inspect model scores, and manage meeting rooms.

## TypeScript Tooling

The repository also includes a TypeScript implementation and Prisma schema.

```powershell
npm install
npm run build
npm run dev
```

Useful database commands for that stack:

```powershell
npm run db:up
npm run db:generate
npm run db:migrate
npm run db:seed
```

## Project Layout

```text
app/            FastAPI application, agent core, services, routes, and database models
mcp_server/     Model Context Protocol server
migrations/     Alembic database migrations
prisma/         Prisma schema and migrations for the TypeScript stack
soul/           Agent identity and behavior specification
src/            TypeScript implementation and tooling
docker/          Local PostgreSQL/pgvector environment
```

## Security Notes

- Keep API keys, database credentials, and JWT secrets in `.env` only.
- Replace all example credentials before using the service outside local development.
- Restrict CORS origins and protect the workspace path before exposing the server publicly.

## License

No license has been declared for this repository yet.

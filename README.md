# Xanax

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

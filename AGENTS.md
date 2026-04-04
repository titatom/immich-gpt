# AGENTS.md

## Cursor Cloud specific instructions

### Overview

immich-gpt is a self-hosted web app with a Python/FastAPI backend and React/TypeScript frontend. It connects to an external Immich photo server and uses OpenAI for AI-based metadata enrichment of photos.

### Services

| Service | Command | Port | Notes |
|---------|---------|------|-------|
| Backend API | `cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000` | 8000 | Set `DATABASE_URL=sqlite:///./data/immich_gpt.db` and `REDIS_URL=redis://localhost:6379/0` |
| Frontend dev | `cd frontend && npx vite --host 0.0.0.0 --port 3000` | 3000 | Proxies `/api` to backend at port 8000 |
| Redis | `redis-server --daemonize yes` | 6379 | Must be running before starting backend/worker |
| RQ Worker | `cd backend && python3 -m app.workers.rq_worker` | — | Executes background jobs; requires Redis |

### Running tests

```bash
# Backend (134 tests — all use in-memory SQLite, no external services required)
cd backend && python3 -m pytest tests/ -v

# Frontend (46 tests — Vitest + React Testing Library, jsdom)
cd frontend && npm test
```

### Lint / type-check

```bash
# Backend: no dedicated linter; test coverage validates API contracts
cd backend && python3 -m pytest tests/ -v

# Frontend ESLint (flat config, zero warnings enforced)
cd frontend && npm run lint

# Frontend TypeScript
cd frontend && npx tsc --noEmit
```

### Database migrations (Alembic)

The project uses Alembic for schema migrations. `init_db()` automatically applies all pending migrations on startup via `alembic upgrade head`. The initial migration covers all current tables.

```bash
# Apply migrations manually
cd backend && alembic upgrade head

# Generate a new migration after editing models
cd backend && alembic revision --autogenerate -m "describe_change"

# Override the target DB (e.g. for a test DB)
ALEMBIC_DATABASE_URL="sqlite:///./data/test.db" alembic upgrade head
```

### Build

Frontend builds to `backend/static/` so FastAPI can serve it in production:

```bash
cd frontend && npx vite build
```

### Key gotchas

- The `pip install` bin directory (`~/.local/bin`) must be on `PATH` for `uvicorn`, `pytest`, `alembic`, etc. Add `export PATH="$HOME/.local/bin:$PATH"` to your shell profile.
- Redis is **optional**. Set `REDIS_URL=""` (or leave unset) and jobs run in-process via `ThreadPoolExecutor`. Only set `REDIS_URL` when using the full multi-container stack.
- The backend `config.py` reads `.env` from CWD, so run the backend from `backend/` directory.
- External services (Immich server, OpenAI API) require secrets (`IMMICH_URL`, `IMMICH_API_KEY`, `OPENAI_API_KEY`) but are not needed for tests or basic UI development.
- Frontend devDependencies now include `eslint`, `@typescript-eslint/*`, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh`, `vitest`, `@vitest/coverage-v8`, `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/user-event`, and `jsdom`.

### Docker / Unraid packaging

- Single-container image: `docker build -f Dockerfile.unraid -t immich-gpt .`
- Production GHCR image: `ghcr.io/titatom/immich-gpt:latest`
- See `DOCKER.md` for full deployment docs and the Unraid CA template at `unraid/immich-gpt.xml`.
- GitHub Actions at `.github/workflows/docker.yml` publishes to GHCR on version tags (`v*.*.*`).

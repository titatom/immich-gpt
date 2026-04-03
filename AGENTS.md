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
cd backend && python3 -m pytest tests/ -v
```

All 61 tests use in-memory SQLite and don't require Redis or any external services.

### Lint / type-check

- **Backend**: No dedicated linter configured; tests cover validation.
- **Frontend**: `cd frontend && npx tsc --noEmit` for TypeScript type-checking. The `npm run lint` script references ESLint but ESLint is not installed as a devDependency.

### Build

Frontend builds to `backend/static/` so FastAPI can serve it in production:

```bash
cd frontend && npx vite build
```

### Key gotchas

- The `pip install` bin directory (`~/.local/bin`) must be on `PATH` for `uvicorn`, `pytest`, etc. The update script handles this.
- Redis must be installed via `sudo apt-get install -y redis-server` and started with `redis-server --daemonize yes` before the API or worker can connect.
- The backend `config.py` reads `.env` from CWD, so run the backend from `backend/` directory.
- External services (Immich server, OpenAI API) require secrets (`IMMICH_URL`, `IMMICH_API_KEY`, `OPENAI_API_KEY`) but are not needed for tests or basic UI development.

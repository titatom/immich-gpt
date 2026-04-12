# Development Guide

This guide is for contributors who want to run `immich-gpt` from source instead of Docker.

## Prerequisites

- Python 3.12
- Node.js 18+
- npm
- Optional: Redis if you want to test the RQ worker path

External services such as Immich, OpenAI, or OpenRouter are not required to run the automated tests, but they are required to exercise the full sync and classification flow manually.

## Repository layout

- `backend/` — FastAPI app, database models, services, and tests
- `frontend/` — React + TypeScript single-page app
- `docs/` — end-user and operator documentation
- `docker-compose.yml` — recommended production deployment

## Backend

Run the backend from the `backend/` directory so the settings loader reads the correct `.env` file.

1. Create a virtual environment and install dependencies:

   ```bash
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Create a `.env` file or export variables:

   ```bash
   SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
   export SECRET_KEY
   export DATABASE_URL=sqlite:///./data/immich_gpt.db
   export REDIS_URL=
   ```

3. Start the API:

   ```bash
   cd backend
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   ```

The backend automatically applies Alembic migrations on startup.

## Frontend

Start the Vite development server from `frontend/`:

```bash
cd frontend
npm install
npx vite --host 0.0.0.0 --port 3000
```

The Vite config proxies `/api` requests to `http://localhost:8000`, so run the backend first.

## Optional Redis worker

The default development flow runs jobs in-process. If you want to test Redis-backed execution:

1. Start Redis:

   ```bash
   redis-server --daemonize yes
   ```

2. Set `REDIS_URL=redis://localhost:6379/0`.

3. Start a worker:

   ```bash
   cd backend
   python3 -m app.workers.rq_worker
   ```

## Useful local URLs

- Frontend dev server: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Health check: `http://localhost:8000/health`
- OpenAPI docs: `http://localhost:8000/docs`

## Test and quality commands

Run focused checks from the relevant project directory:

### Backend

```bash
cd backend
python3 -m pytest tests/ -v
```

### Frontend tests

```bash
cd frontend
npm test
```

### Frontend lint

```bash
cd frontend
npm run lint
```

### Frontend type-check

```bash
cd frontend
npx tsc --noEmit
```

## Development workflow

1. Start backend and frontend.
2. Complete the first-run setup wizard.
3. Configure Immich and an AI provider in **Settings**.
4. Use **Dashboard** to sync assets and run classification.
5. Review and approve results from **Review**.
6. Inspect **Jobs** and **Logs** when debugging.

## Common contributor pitfalls

- Run the backend from `backend/`, not the repo root, so `.env` is loaded correctly.
- Do not forget `SECRET_KEY`; startup validation rejects empty or weak values.
- Leave `REDIS_URL` empty unless you actually want the Redis/RQ path.
- If you split frontend and backend across different origins, set `CORS_ORIGINS` explicitly.
- If you test behind HTTPS, set `SESSION_COOKIE_SECURE=true`.

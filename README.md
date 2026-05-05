# FitGen AI

FitGen AI is a production-grade starter system for adaptive personal fitness planning. It is not a chatbot: the backend keeps persistent user state, tracks workout history, adapts plans from feedback, and generates India-friendly diet plans within budget constraints.

## What It Includes

- FastAPI backend with SQLAlchemy persistence
- PostgreSQL-ready configuration through `DATABASE_URL`
- SQLite default for local demos
- Stateful user profile, workout plans, logs, feedback, diet plans, and weekly reviews
- Rule-based workout planner with equipment fallback and progressive overload
- Hybrid LLM hook for coach-style plan summaries when `OPENAI_API_KEY` is set
- India-friendly diet planner with budget and vegetarian/non-vegetarian constraints
- Clean dashboard UI with progress charts, workout logging, diet budget breakdown, feedback, and exportable weekly report
- Demo data seeding endpoint for quick product walkthroughs

## Run Locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000`.

On first launch, the dashboard asks for a real profile instead of loading demo data automatically. Use **Create adaptive plan** for your own profile, or **Load demo profile** when you want seeded workout history.

On Windows, you can also run:

```powershell
powershell -ExecutionPolicy Bypass -File .\run-fitgen.ps1 8010
```

Then open `http://127.0.0.1:8010`.

SQLite local demos auto-create tables on startup. For managed databases, use migrations instead.

## PostgreSQL

By default, FitGen AI uses `sqlite:///./fitgen.db`. To use PostgreSQL:

```bash
set DATABASE_URL=postgresql+psycopg://fitgen:fitgen@localhost:5432/fitgen_ai
set AUTO_CREATE_TABLES=false
alembic upgrade head
uvicorn app.main:app --reload
```

For Linux/macOS shells:

```bash
export DATABASE_URL=postgresql+psycopg://fitgen:fitgen@localhost:5432/fitgen_ai
export AUTO_CREATE_TABLES=false
alembic upgrade head
uvicorn app.main:app --reload
```

Copy `.env.example` to `.env` for local configuration. Keep secrets out of Git.

## Database Migrations

FitGen AI uses Alembic for schema versioning:

```bash
alembic upgrade head
alembic revision --autogenerate -m "describe change"
```

The first migration creates users, workout plans, workout exercises, workout logs, feedback, diet plans, and weekly reviews.

## Optional LLM Enrichment

The adaptive logic works without an LLM. To add concise coach-style reasoning summaries:

```bash
set OPENAI_API_KEY=your_key_here
set LLM_MODEL=gpt-4o-mini
```

## Accounts

FitGen AI supports lightweight local accounts:

- Signup creates an account plus the first training profile.
- Passwords are stored with PBKDF2-SHA256 hashes, not plaintext.
- Browser sessions use bearer tokens stored in `localStorage`.
- Demo mode remains available and creates an unowned local profile for testing.
- Workout logs can be attached directly to planned exercises, so weekly completion and replanning are based on the actual schedule.

This is suitable for a product prototype. Before public deployment, add token expiry, refresh/revocation policy, HTTPS-only hosting, and stronger account recovery flows.

## API Highlights

- `GET /api/bootstrap` creates and returns a demo user
- `GET /api/users/{user_id}/dashboard` returns the full dashboard payload
- `POST /api/users/{user_id}/plans/weekly` generates a new weekly plan
- `POST /api/users/{user_id}/workouts/logs` records performance
- `POST /api/users/{user_id}/feedback` adapts next planning decisions
- `POST /api/users/{user_id}/weekly-review` creates a weekly review
- `GET /api/users/{user_id}/report/export` exports a plain-text weekly report

## Architecture

```mermaid
flowchart LR
    U["User Dashboard"] --> API["FastAPI API"]
    API --> DB[("PostgreSQL / SQLite")]
    API --> WP["Workout Planner"]
    API --> DP["Diet Planner"]
    API --> FR["Feedback Loop"]
    API --> WR["Weekly Review"]
    WP --> DB
    DP --> DB
    FR --> WP
    WR --> WP
    API -. optional .-> LLM["OpenAI / Local LLM"]
```

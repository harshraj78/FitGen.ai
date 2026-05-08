# FitGen AI

FitGen AI is a production-grade starter system for adaptive personal fitness planning. It is not a chatbot: the backend keeps persistent user state, tracks workout history, adapts plans from feedback, and generates India-friendly diet plans within budget constraints.

## What It Includes

- FastAPI backend with SQLAlchemy persistence
- PostgreSQL-ready configuration through `DATABASE_URL`
- SQLite default for local demos
- Stateful user profile, workout plans, workout sessions, set-level logs, feedback, diet plans, and weekly reviews
- Rule-based workout planner with equipment fallback and progressive overload
- Session Engine with readiness check-ins, partial session recovery, skipped exercises, and set-by-set performance capture
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

The first migration creates users, workout plans, workout exercises, workout logs, feedback, diet plans, and weekly reviews. Later migrations add accounts, planned-exercise log links, and the v2 Session Engine tables:

- `workout_sessions`
- `readiness_checkins`
- `workout_session_exercises`
- `performed_sets`

New session flows write set-level records and also maintain aggregate `workout_logs` rows for dashboard and weekly-review compatibility.

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
- Active workout sessions are recovered from the backend after refresh, so in-progress training is not lost when the browser reloads.

## Session Engine

The v2 workout flow treats a live workout as a first-class backend resource. A session starts from a planned training day, copies its planned exercises into `workout_session_exercises`, records optional readiness data, and then accepts set-level logs through `performed_sets`.

This keeps the existing MVP analytics stable while preparing the system for richer adaptation later:

- `workout_sessions` stores lifecycle state: active, completed, or abandoned.
- `readiness_checkins` captures energy, sleep, soreness, stress, and pain before training.
- `workout_session_exercises` tracks per-exercise session status: pending, in progress, completed, or skipped.
- `performed_sets` stores reps, weight, effort, pain flags, and notes for each set.
- `workout_logs` remains as a compatibility summary table used by the dashboard, reports, and weekly review.

The frontend now supports starting a session, logging individual sets, skipping remaining exercises, finishing only after all exercises are resolved, and recovering an active session after page refresh.

This is suitable for a product prototype. Before public deployment, add token expiry, refresh/revocation policy, HTTPS-only hosting, and stronger account recovery flows.

## API Highlights

- `GET /api/bootstrap` creates and returns a demo user
- `GET /api/users/{user_id}/dashboard` returns the full dashboard payload
- `POST /api/users/{user_id}/plans/weekly` generates a new weekly plan
- `POST /api/users/{user_id}/sessions/start` starts or resumes an active workout session
- `GET /api/users/{user_id}/sessions/active` returns the in-progress session for refresh recovery
- `POST /api/sessions/{session_id}/exercises/{session_exercise_id}/sets` logs one performed set
- `POST /api/sessions/{session_id}/exercises/{session_exercise_id}/skip` skips a session exercise
- `POST /api/sessions/{session_id}/finish` completes a fully resolved session
- `POST /api/sessions/{session_id}/abandon` abandons an active session
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
    API --> SE["Session Engine"]
    API --> DP["Diet Planner"]
    API --> FR["Feedback Loop"]
    API --> WR["Weekly Review"]
    WP --> DB
    SE --> DB
    SE --> WL["Aggregate workout_logs"]
    WL --> DB
    DP --> DB
    FR --> WP
    WR --> WP
    API -. optional .-> LLM["OpenAI / Local LLM"]
```

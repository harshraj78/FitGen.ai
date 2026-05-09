# FitGen.ai

FitGen.ai is evolving into an AI-powered gym retention and coaching operating platform for multi-tenant B2B gym operations. The product focus is business-first: retention intelligence, renewal forecasting, revenue operations, trainer performance, operational follow-up workflows, and transformation tracking.

The coaching engine still supports adaptive workout and diet planning, but AI now assists gym teams instead of replacing them. The system is designed to help gym owners and trainers answer the daily operating question: "Which members need action today?"

## What It Includes

- FastAPI backend with SQLAlchemy persistence
- PostgreSQL-ready configuration through `DATABASE_URL`
- SQLite default for local demos
- Multi-tenant organizations with RBAC roles for gym owners, admins, trainers, nutritionists, members, and super admins
- Org-scoped members, trainer assignments, membership plans, memberships, payments, attendance, goals, and audit logs
- Renewal risk scoring using attendance decline, missed workouts, inactivity, adherence drop, goal stagnation, expired memberships, and trainer engagement gaps
- Revenue operations analytics for MRR, active memberships, expiring memberships, unpaid members, renewal trends, retention trends, and churn-risk summaries
- Trainer performance analytics for retention rate, adherence, goal success, active clients, consistency trends, overdue approvals, inactive clients, and high-risk clients
- Retention workflow foundation for inactive member alerts, renewal reminders, trainer follow-ups, pending approval actions, stalled progress alerts, and high churn-risk queues
- Transformation tracking with body metric snapshots, strength progression, consistency improvement, goal history, and transformation milestones
- Stateful workout plans, workout sessions, set-level logs, feedback, diet plans, and weekly reviews
- Rule-based workout planner with equipment fallback and progressive overload
- Session Engine with readiness check-ins, partial session recovery, skipped exercises, and set-by-set performance capture
- Normalized exercise catalog with canonical exercise IDs, aliases, substitutions, movement patterns, and equipment metadata
- Hybrid LLM hook for coach-style plan summaries when `OPENAI_API_KEY` is set
- India-friendly diet planner with budget and vegetarian/non-vegetarian constraints

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

Exercise normalization adds `exercises`, `exercise_aliases`, and `exercise_substitutions`. Existing name-based workout history remains valid, while new planned and session exercises can also link to canonical `exercise_id` values.

## Business Operations APIs

The B2B operating layer is exposed under organization-scoped API routes:

- `GET /api/organizations/{organization_id}/business/dashboard` returns a gym-owner dashboard with revenue, renewal forecast, trainer performance, daily actions, and at-risk members.
- `GET /api/organizations/{organization_id}/business/retention/renewal-risk` returns members most likely to not renew.
- `GET /api/organizations/{organization_id}/business/retention/forecast` forecasts expiring memberships, expected renewals, and revenue at risk.
- `POST /api/organizations/{organization_id}/business/retention/risks/refresh` persists renewal risk snapshots for auditability and trend tracking.
- `GET /api/organizations/{organization_id}/business/revenue` returns MRR, active memberships, unpaid members, renewal trends, retention trends, and churn-risk summaries.
- `GET /api/organizations/{organization_id}/business/trainers/performance` compares trainer effectiveness for gym owners.
- `GET /api/organizations/{organization_id}/business/actions/today` returns the operational action queue.
- `GET /api/organizations/{organization_id}/business/actions/by-type/{workflow_type}` returns focused queues such as inactive members, overdue renewals, pending approvals, stalled progress, and high-risk churn.
- `POST /api/organizations/{organization_id}/business/members/{member_id}/body-metrics` records transformation body metrics.
- `POST /api/organizations/{organization_id}/business/members/{member_id}/transformation-milestones` records transformation milestones.
- `GET /api/organizations/{organization_id}/business/members/{member_id}/transformation` returns member transformation summaries.
- `GET /api/organizations/{organization_id}/business/transformations/gym` returns gym-wide transformation metrics.

These routes use existing organization RBAC helpers. Gym-wide business views require owner/admin access, while trainer-facing queues and trainer performance endpoints are scoped to the authenticated trainer where appropriate.

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

## Exercise Catalog

FitGen keeps exercise names for user-facing display, but v2 also stores canonical exercise records. This gives future adaptation logic a stable identity for movement patterns, substitutions, equipment-aware fallbacks, and pain-aware rules without breaking older logs that only have `exercise_name`.

This is suitable for a product prototype. Before public deployment, add token expiry, refresh/revocation policy, HTTPS-only hosting, and stronger account recovery flows.

## API Highlights

- `GET /api/organizations/{organization_id}/business/dashboard` returns the gym-owner operating dashboard
- `GET /api/organizations/{organization_id}/business/actions/today` returns operational daily actions
- `GET /api/organizations/{organization_id}/business/revenue` returns revenue operations metrics
- `GET /api/organizations/{organization_id}/business/trainers/performance` compares trainer effectiveness
- `GET /api/organizations/{organization_id}/business/retention/forecast` returns renewal forecast analytics
- `GET /api/organizations/{organization_id}/trainer/clients` returns trainer-assigned clients
- `GET /api/organizations/{organization_id}/trainer/plan-approvals/pending` returns pending trainer approvals
- `GET /api/bootstrap` creates and returns a demo user
- `GET /api/users/{user_id}/dashboard` returns the legacy member dashboard payload
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
    OWNER["Gym Owner Dashboard"] --> API["FastAPI API"]
    TRAINER["Trainer Workspace"] --> API
    MEMBER["Member Coaching UI"] --> API
    API --> DB[("PostgreSQL / SQLite")]
    API --> RI["Retention Intelligence"]
    API --> RO["Revenue Operations"]
    API --> TP["Trainer Performance"]
    API --> RA["Retention Automation"]
    API --> TS["Transformation Tracking"]
    API --> WP["Workout Planner"]
    API --> SE["Session Engine"]
    API --> DP["Diet Planner"]
    API --> N["Notifications"]
    RI --> DB
    RO --> DB
    TP --> DB
    RA --> N
    RA --> DB
    TS --> DB
    WP --> DB
    SE --> DB
    SE --> WL["Aggregate workout_logs"]
    WL --> DB
    DP --> DB
    API -. optional .-> LLM["OpenAI / Local LLM"]
```

The architecture keeps business operations separate from coaching generation. Retention, revenue, trainer performance, automation, and transformation services aggregate existing org-scoped data and can scale toward background jobs, materialized snapshots, and external channels such as email, WhatsApp, and push notifications.

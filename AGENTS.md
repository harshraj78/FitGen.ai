# AGENTS.md

Production operating guide for Codex and other AI coding agents working on FitGen.ai.

## Product Mission

FitGen.ai is a B2B gym retention and coaching operating platform. The product is for gym owners, admins, trainers, nutritionists, and members. The core business question is:

> Which members need action today, and what should the gym team do next?

Prioritize work that makes the product safer, clearer, and more useful for real gym operations: retention risk, renewals, trainer follow-ups, member onboarding, workout execution, transformation tracking, and operational visibility.

## Current Production Posture

The app has been deployed as an early production/private-pilot system:

- Backend: FastAPI, SQLAlchemy, Alembic, PostgreSQL-ready.
- Frontend: `frontend-modern`, React + Vite + Tailwind.
- Deployment targets: Render backend, Vercel frontend.
- Docker support: root `Dockerfile`, `docker-compose.yml`, `frontend-modern/Dockerfile`.
- CI: `.github/workflows/ci.yml`.
- Demo seed routes should be disabled in production.

Treat this as a real business-user product, not a throwaway prototype. Avoid shortcuts that leak data across gyms, weaken auth, or make deployment unreliable.

## Repository Map

- `app/main.py`: FastAPI app, auth endpoints, legacy member dashboard endpoints, demo route gating, router registration.
- `app/config.py`: environment-driven settings.
- `app/db.py`: SQLAlchemy engine/session setup and SQLite/Postgres handling.
- `app/models.py`: SQLAlchemy models for accounts, organizations, memberships, workouts, retention, business operations, notifications, and transformation tracking.
- `app/schemas.py`: Pydantic request/response schemas.
- `app/routes/`: organization, business, trainer, session, audit, analytics, and notification routes.
- `app/services/`: domain logic for auth, tenancy, business ops, demo seeding, workout planning, session execution, analytics, notifications, and reviews.
- `migrations/`: Alembic migrations. Never edit applied migrations casually.
- `frontend-modern/`: primary modern frontend for production.
- `frontend/`: older static frontend kept for compatibility/reference.
- `render.yaml`: Render backend + Postgres blueprint.
- `frontend-modern/vercel.json`: Vercel frontend deployment config.

## Non-Negotiable Engineering Rules

1. Preserve tenant isolation.
   Every organization-scoped route must verify membership and role. Never query organization data without filtering by `organization_id`.

2. Keep production demo routes disabled by default.
   `APP_ENV=production` must not expose `/api/bootstrap` or `/api/demo/business` unless `ENABLE_DEMO_ROUTES=true` is deliberately set for a temporary private test.

3. Do not weaken auth.
   Sessions have TTL and logout revocation. Do not reintroduce non-expiring sessions, plaintext secrets, or frontend-only access control.

4. Use Alembic for schema changes.
   If models change database shape, add a migration and verify `alembic heads`.

5. Keep deployment env-driven.
   No hardcoded Render, Vercel, database, API-key, or domain secrets in source. Use env vars.

6. Do not make broad rewrites during launch stabilization.
   Prefer focused patches that preserve existing workflows and can be deployed safely.

7. Frontend must match backend contracts.
   If backend serializes exercise fields as `name`, do not read only `exercise_name`. Prefer typed API models when touching data-heavy screens.

## Production Environment

Backend production env vars:

```text
APP_ENV=production
DATABASE_URL=<production Postgres URL from Render/Neon/Supabase>
AUTO_CREATE_TABLES=true
ENABLE_DEMO_ROUTES=true
ALLOWED_ORIGINS=https://fit-gen-ai-orcin.vercel.app
SESSION_TTL_HOURS=168
```

Optional LLM env vars:

```text
LLM_PROVIDER=groq
GROQ_API_KEY=<Groq API key stored only in Render env vars>
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-20b
```

Frontend production env vars:

```text
VITE_API_BASE_URL=https://fitgen-ai.onrender.com
```

Render backend health check:

```text
GET /api/health
```

Expected:

```json
{"status":"ok","service":"FitGen AI"}
```

## Deployment Notes

Preferred free/private-pilot stack:

- Render free web service for backend.
- Neon or Supabase free Postgres if Render Postgres is paid/unavailable.
- Vercel free frontend for `frontend-modern`.

Important details:

- Render Docker must bind to `$PORT`.
- Root backend Docker command runs migrations before boot:

```text
alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

- If frontend receives CORS errors, set backend `ALLOWED_ORIGINS` to the exact Vercel URL and redeploy backend.
- Do not leave `ALLOWED_ORIGINS=*` for real users.

## Checks To Run

Before committing production-impacting backend changes:

```powershell
python -m compileall app
alembic heads
```

In this Codex environment, plain `python` may not be on PATH. Use the bundled Python if needed:

```powershell
& 'C:\Users\Utkarsh Raj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m compileall app
& 'C:\Users\Utkarsh Raj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m alembic heads
```

Before committing frontend changes:

```powershell
cd frontend-modern
npm run lint
npm run build
```

Useful smoke tests:

- `GET /api/health`
- login via `/api/auth/login`
- `/api/auth/me` with bearer token
- `/api/auth/logout` revokes token
- production mode returns `404` for `/api/bootstrap` and `/api/demo/business`
- organization business dashboard loads only for authorized org members

## UI/UX Standards

FitGen.ai is an operational SaaS product, not a marketing site.

- Prioritize clear dashboards, dense but readable information, and fast workflows.
- Avoid oversized hero sections inside the authenticated app.
- Business users need immediate access to actions, retention, trainers, renewals, and member status.
- Mobile business navigation must remain usable.
- Member workout screens must be mobile-first and usable during an active gym session.
- Empty states should guide new gyms to create members, staff, plans, and memberships.
- Do not expose placeholder pages to production users unless clearly marked and non-blocking.

## Security And Privacy Requirements

Treat all member health, attendance, payment, and transformation data as sensitive.

Required before broad public launch:

- Rate limiting for auth and public endpoints.
- Password reset flow.
- Tenant-isolation tests for all organization routes.
- Better staff/member invite flow.
- Audit-log UI for important admin actions.
- Data export/deletion policy.
- Privacy Policy and Terms.
- Monitoring/error tracking.
- Database backup and restore procedure.

When making changes:

- Never log passwords, tokens, API keys, or full auth headers.
- Avoid returning sensitive internal metadata in API responses.
- Verify role checks for owner/admin/trainer/nutritionist/member paths.

## High-Priority Product Backlog

Work in this order unless the user explicitly redirects:

1. Business signup and create-gym workspace UI.
2. Add/import members from the business UI.
3. Staff invite and role management.
4. Membership plan and payment entry UI.
5. Real member detail page with retention, payments, goals, attendance, and transformation.
6. Action queue workflows: assign, complete, snooze, note, follow-up outcome.
7. Modern member workout session UI wired to session APIs.
8. Goals page implementation.
9. Password reset and auth rate limiting.
10. Tenant isolation/API tests.
11. Monitoring and production observability.

## Git Workflow

- Default branch is `master`.
- Use `<short-description>` for working branches.
- Check worktree status before edits.
- Do not overwrite user changes.
- Commit focused, deployable changes.
- Run relevant checks before commit.
- Push branches when the user asks for GitHub updates.

## Known Current Gaps

- Business login exists, but public business signup UI is not complete.
- First owner account may currently be created through API if signup UI is missing.
- Demo workspace button should fail in production unless demo routes are explicitly enabled.
- Free Render instances sleep after inactivity and can delay first requests.
- Vite/esbuild moderate dev-server advisory may remain until Vite is upgraded; production static Vercel build is less exposed, but upgrade should still be scheduled.

## Agent Behavior

When continuing work:

1. Fetch/pull or inspect latest Git state first if the user says deployment/GitHub changed.
2. Read nearby backend and frontend code before editing.
3. Make the smallest production-safe change.
4. Run checks.
5. Explain what changed, what was verified, and what remains.

If production is broken:

1. Ask for the failing URL and last deploy logs if not available.
2. Prioritize restoring `/api/health`, login, and dashboard loading.
3. Avoid speculative large rewrites.
4. Patch, verify, commit, and push.

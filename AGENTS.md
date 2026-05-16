# AGENTS.md

Production operating guide for Codex and other AI coding agents working on FitGen.ai.

## Mission

FitGen.ai is a B2B gym retention, renewal, and coaching operating system. The primary user is a gym owner or admin who needs a clear answer every morning:

> Which members need action today, and what should the gym team do next?

Prioritize work that improves real gym operations: member onboarding, attendance visibility, silent dropout detection, renewals, payment follow-up, WhatsApp-ready communication, workout execution, and transformation tracking.

## Production Posture

FitGen.ai is an early production/private-pilot product, not a throwaway prototype.

- Backend: FastAPI, SQLAlchemy, Pydantic, Alembic.
- Frontend: `frontend-modern`, React, Vite, TypeScript, Tailwind.
- Database: PostgreSQL in production, SQLite for local demos.
- Deployment: Render backend, Vercel frontend.
- Docker: root `Dockerfile`, `docker-compose.yml`, `frontend-modern/Dockerfile`.
- CI: `.github/workflows/ci.yml`.

Demo routes must be disabled for real users.

## Repository Map

- `app/main.py`: FastAPI app, auth endpoints, member invite acceptance, demo route gating, legacy member APIs.
- `app/config.py`: environment-driven settings.
- `app/db.py`: SQLAlchemy engine/session setup.
- `app/models.py`: SQLAlchemy models.
- `app/schemas.py`: Pydantic request/response contracts.
- `app/routes/organizations.py`: organizations, members, invites, attendance import, plans, memberships, payments.
- `app/routes/business.py`: business dashboard, retention intelligence, daily actions, workflow updates.
- `app/services/business_ops.py`: revenue, retention, Indian-market automations, transformation summaries.
- `app/services/auth.py`: password hashing, sessions, invite token helpers.
- `frontend-modern/`: production frontend.
- `migrations/`: Alembic migrations.

## Non-Negotiable Rules

1. Preserve tenant isolation.
   Every organization-scoped query must filter by `organization_id` and enforce role membership.

2. Do not weaken auth.
   Keep password hashing, session TTL, logout revocation, and role checks intact.

3. Keep production env-driven.
   Never hardcode Render URLs, Vercel URLs, database URLs, API keys, WhatsApp credentials, or payment secrets.

4. Use Alembic for schema changes.
   Any model field that changes persistence needs a migration.

5. Keep demo routes disabled by default in production.
   `APP_ENV=production` should not expose demo seed routes unless deliberately enabled for a private test.

6. Do not fake external integrations.
   WhatsApp and payment links may be provider-ready metadata, but do not mark delivery or payment as successful without provider webhook verification.

7. Keep launch patches focused.
   Avoid broad rewrites. Make deployable, testable changes that preserve current workflows.

## Indian Gym Product Assumptions

- Many gyms are owner-led and may not have multiple trainers.
- WhatsApp is the primary operational communication channel.
- QR/biometric attendance is a major retention signal.
- UPI is essential for collections, alongside cards and netbanking.
- Owners need simple action queues more than complex analytics.

Important product flows:

- Silent dropout alarm after 7 days without QR/biometric scan.
- Renewal funnel at 15, 7, and 3 days before expiry.
- Member profile first, member login later through invite acceptance.
- Owner/admin fallback assignee when no trainer exists.

## Production Environment

Backend:

```text
APP_ENV=production
DATABASE_URL=<production-postgres-url>
AUTO_CREATE_TABLES=false
ENABLE_DEMO_ROUTES=false
ALLOWED_ORIGINS=https://your-vercel-app.vercel.app
SESSION_TTL_HOURS=168
FRONTEND_APP_URL=https://your-vercel-app.vercel.app
```

Optional automation config:

```text
WHATSAPP_AUTOMATION_ENABLED=false
PAYMENT_LINKS_ENABLED=false
BOOKING_BASE_URL=https://your-vercel-app.vercel.app/book
PAYMENT_LINK_BASE_URL=<payment-provider-link-base>
```

Optional LLM config:

```text
LLM_PROVIDER=groq
GROQ_API_KEY=<store only in hosting env vars>
LLM_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-20b
```

Frontend:

```text
VITE_API_BASE_URL=https://your-render-api.onrender.com
```

## Checks

Backend:

```powershell
python -m compileall app
alembic heads
```

If plain `python` is unavailable in Codex:

```powershell
& 'C:\Users\Utkarsh Raj\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' -m compileall app
```

Frontend:

```powershell
cd frontend-modern
npm run lint
npm run build
```

Smoke tests:

- `GET /api/health`
- business login/logout
- create member with phone/email
- invite member and accept invite
- list member detail
- import QR/biometric attendance
- generate daily actions
- complete/dismiss daily actions
- production demo routes return 404 when disabled

## UI/UX Standards

FitGen.ai is an operational SaaS product.

- Prefer dense, readable dashboards over marketing layouts.
- Make owner actions obvious: invite, follow up, complete, dismiss, renew.
- Mobile business navigation must remain usable.
- Member workout screens must be mobile-first.
- Empty states should guide setup without exposing placeholder-only pages.
- Avoid UI controls that do nothing.

## Security and Privacy

Treat member health, attendance, payment, and transformation data as sensitive.

Required before broad public launch:

- Auth rate limiting.
- Password reset.
- Tenant-isolation tests.
- Real WhatsApp provider integration with template approval and delivery state.
- Real payment gateway integration with webhook verification.
- Audit-log UI.
- Data export/deletion policy.
- Privacy Policy and Terms.
- Error monitoring.
- Backup/restore procedure.

## Backlog Priority

1. Stabilize member signup/invite/account linking.
2. Build member detail and action history workflows.
3. Connect QR/biometric attendance import to real devices.
4. Add payment gateway adapter and verified webhooks.
5. Add WhatsApp provider adapter and delivery tracking.
6. Add scheduler for daily automation runs.
7. Add password reset and auth rate limiting.
8. Add tenant-isolation tests.
9. Add monitoring and operational runbooks.

## Git Workflow

- Default branch: `master`.
- Current active launch branch may be `frontend-fixes`.
- Check `git status -sb` before edits.
- Never overwrite user changes.
- Commit focused, deployable changes.
- Run relevant checks before commit.
- Push when the user requests GitHub updates.

## Agent Behavior

When continuing work:

1. Inspect Git state first.
2. Read nearby code before editing.
3. Make the smallest production-safe change.
4. Run checks.
5. Report what changed, what passed, and what remains.

If production is broken:

1. Prioritize `/api/health`, auth, dashboard loading, and CORS.
2. Ask for deploy logs if local context is insufficient.
3. Avoid speculative rewrites.
4. Patch, verify, commit, and push.

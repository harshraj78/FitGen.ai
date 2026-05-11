# FitGen.ai Modern Frontend

This is the React migration target for FitGen.ai.

It intentionally lives beside the legacy static frontend while the product moves toward a modern dual-experience SaaS UI:

- `/business/login` and `/business/*` for gym owners, admins, trainers, retention workflows, revenue operations, and trainer performance.
- `/app/login` and `/app/*` for members, workout tracking, goals, progress, and transformation.

## Stack

- React
- React Router
- TanStack Query
- Tailwind CSS
- shadcn/ui-compatible local primitives
- Vite

## Run

Install dependencies, then run:

```bash
npm install
npm run dev
```

The Vite dev server proxies `/api` to `http://127.0.0.1:8010`, matching the existing FastAPI local server.

## Production Build

FastAPI now serves this app when `frontend-modern/dist` exists:

```bash
npm run build
cd ..
uvicorn app.main:app --reload
```

Then open `/business/login` or `/app/login` from the FastAPI server. If `dist` does not exist, FastAPI falls back to the legacy static frontend.

## Demo

Use **Load demo gym workspace** on `/business/login`, or sign in with:

- Owner: `owner@fitgen.demo`
- Trainer: `trainer@fitgen.demo`
- Member: `member@fitgen.demo`
- Password: `fitgen-demo`

## Migration Notes

Backend APIs are reused as-is. This app connects to real endpoints for authentication, organizations, business dashboard data, trainer workspace data, and member dashboard data.

The legacy `frontend/` folder remains available until the React app is ready to become the FastAPI-served production frontend.

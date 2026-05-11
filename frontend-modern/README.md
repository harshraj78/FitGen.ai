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

## Migration Notes

Backend APIs are reused as-is. This app connects to real endpoints for authentication, organizations, business dashboard data, trainer workspace data, and member dashboard data.

The legacy `frontend/` folder remains available until the React app is ready to become the FastAPI-served production frontend.

# ASTRA frontend

React/Vite interface for the Cognivault local workbench.

## Phase 9A–9B integration

The frontend currently integrates the backend's supported baseline:

- JWT login through `POST /api/v1/auth/login`
- session validation through `GET /api/v1/auth/me`
- protected application routes
- local logout by discarding the stateless access token
- authenticated text execution through `POST /api/v1/agent/run`
- normalized agent response, steps, citations, execution time, and air-gap flag
- health display through `GET /health`

Tokens are stored in `sessionStorage`, so closing the browser tab ends the
frontend session. The backend remains the authority for authentication and
RBAC. Public registration creates a basic `user`, while agent execution
requires an existing `admin`, `officer`, or `worker` account.

Primary employee navigation contains Dashboard, AI Workbench, Document
Analysis, and Generated Files. Document Analysis and Generated Files preserve
their product workspaces with truthful pending/empty states because matching
backend APIs do not exist. Knowledge Base, Agent Execution, and Chatbot are no
longer primary navigation items; their earlier components remain in source for
possible future administrative or Workbench reuse.

To create a local development account authorized for text-agent execution,
follow the development worker instructions in `backend/README.md`. No
development credentials are stored in the frontend.

## Local development

Start FastAPI at `http://127.0.0.1:8000`, then:

```bash
npm install
npm run dev
```

Vite proxies `/api` and `/health` to FastAPI. This keeps browser calls
same-origin during development, so backend CORS changes are not required.

For a deployment where the API is served from a different origin, copy
`.env.example` to a local `.env` and set:

```text
VITE_API_BASE_URL=http://your-api-host:8000
```

That deployment will also need an explicit, restricted backend CORS policy.
Do not place JWT secrets or other server credentials in Vite environment
variables; all `VITE_` variables are exposed to browser code.

## Checks

```bash
npm run lint
npm run build
```

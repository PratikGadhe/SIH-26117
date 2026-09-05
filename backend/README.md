# Cognivault Backend

The Cognivault backend is a local FastAPI application for the sovereign AI
workbench. Phase 5 adds a protected boundary to the teammate-owned LangGraph
workflow on top of the SQLite, JWT, RBAC, and audit foundations.

## Requirements

- Python 3.11 or newer

## Implemented through Phase 5

- Versioned FastAPI routing and health checks
- SQLite user and audit persistence
- Argon2id password hashing
- Expiring JWT bearer authentication
- Explicit role-based authorization
- Security-event audit logging
- Administrator-only, filtered audit retrieval
- Authenticated, role-protected LangGraph execution
- A stable agent service and adapter boundary
- Safe agent output and error normalization
- Safe startup upgrades for databases from earlier phases
- OpenAPI, Swagger UI, and ReDoc documentation

## Agent integration

The backend calls the existing synchronous public function
`agents/agent_service.py::run_agentic_workflow(user_query, image_path=None,
pdf_path=None)`. The adapter preserves all three parameters, imports that entry
point lazily, and translates its result into backend-owned data objects. A
normal backend startup therefore does not require LangGraph or load the
compiled graph. Once loaded successfully, the callable is cached.

```text
FastAPI agent router
        ↓
Backend agent service
        ↓
LangGraph adapter
        ↓
Existing run_agentic_workflow(...)
```

The teammate function is synchronous and invokes a singleton compiled
LangGraph with `agent_graph.invoke(...)`. The API handler is deliberately a
synchronous FastAPI route, so FastAPI runs the blocking handler in its worker
thread pool. Phase 5 does not add a queue, background job system, or artificial
async wrapper.

### Stable backend contract

The Phase 5 endpoint accepts one stateless text execution:

```http
POST /api/v1/agent/run
Authorization: Bearer <access_token>
Content-Type: application/json

{"user_query": "Summarize the maintenance procedure"}
```

`user_query` is trimmed, must be non-blank, and is limited to 10,000 characters.
Unknown request fields are rejected. A successful response has this shape:

```json
{
  "status": "success",
  "response": "...",
  "task_type": "SOP_QUERY",
  "citations": [
    {"source": "manual.pdf", "page": "4", "distance": 0.2}
  ],
  "steps": [
    {"step": 1, "agent": "Supervisor Agent", "action": "Classified task"}
  ],
  "execution_time_seconds": 0.25,
  "air_gapped": true
}
```

This is a normalized subset of the teammate service response. Task type is
restricted to the four values defined by the real agent state and router:
`DIRECT_CHAT`, `HYBRID_AUDIT`, `SOP_QUERY`, and `VISION_INSPECTION`. Internal
graph state, plans, vision data, RAG data, and raw errors are not returned. The
current agent has no conversation/session mechanism, so the API does not
invent a session identifier or database. The backend adapter preserves the
agent's optional server-side `image_path` and `pdf_path` parameters, but the
HTTP schema does not expose client-supplied filesystem paths. Those arguments
remain `None` until a later upload/reference subsystem can provide trusted
server-owned paths. Authenticated identity and credentials are not sent to the
agent because its real interface does not consume them.

The endpoint allows `admin`, `officer`, and `worker`. A missing or invalid JWT
returns 401; an authenticated `user` returns 403 through the existing
`require_roles(...)` policy. Invalid request data returns 422. Normalized agent
failures return 502, unavailable dependencies/model service return 503, and a
reported timeout returns 504. No raw subsystem exception is exposed. The
adapter does not enforce a wall-clock timeout because the existing synchronous
agent interface does not provide cancellation or timeout control.

### Ownership boundary and real-agent requirements

Backend-owned code covers request validation, JWT/RBAC enforcement, the
service/adapter boundary, response normalization, safe HTTP errors, and safe
audit metadata. Agent-owned code covers LangGraph state and nodes, prompts,
routing, Ollama/Qwen configuration, RAG, vision, and synthesis.

Real execution requires the agent environment declared in
`agents/requirements.txt`, including LangGraph/LangChain and `requests`, plus
the local Ollama models and any RAG or vision dependencies needed by the
selected route. These dependencies are intentionally not duplicated in
`backend/requirements.txt` and are not needed for backend startup or tests.
The current backend virtual environment alone therefore returns a safe 503
when the adapter cannot import the agent stack.

The teammate service catches graph exceptions and returns an error dictionary,
which the adapter normalizes. Its synthesizer currently collapses model errors
to the exact sentinel `Report generation failed.` while marking graph status
as successful; the adapter treats that known sentinel as unavailable instead
of returning false success. The public interface loses the original model
error category in this case, so finer classification still requires an
agent-owned contract improvement.

## Audit logging

Audit records provide structured, queryable traceability for security events:

```text
Authentication or authorization event
                  ↓
             Audit service
                  ↓
       SQLite audit_events table
```

The controlled event types are:

- `AUTH_REGISTER_SUCCESS`
- `AUTH_LOGIN_SUCCESS`
- `AUTH_LOGIN_FAILURE`
- `AUTHORIZATION_DENIED`
- `AGENT_EXECUTION_SUCCESS`
- `AGENT_EXECUTION_FAILURE`

Successful authorization is not logged. There is no logout event because the
current stateless access-token design has no server-side logout operation.

The `audit_events` table stores:

- UTC creation timestamp
- controlled event type
- user ID and username when known
- success status
- request resource and action
- direct client IP address when available
- small, event-specific safe metadata

It intentionally does not store passwords, password hashes, JWTs, JWT secrets,
Authorization headers, request bodies, documents, prompts, agent responses,
model outputs, or uploaded files. Agent audit events contain only the user,
resource/action, success state, and either task type or a safe error category.
Forwarded IP headers are not trusted; only the direct peer address supplied by
the server is considered.

Audit writes use a documented availability policy: if SQLite cannot persist an
event, the security decision remains unchanged and a generic warning containing
only the event type is sent to infrastructure logs. A failed audit write never
grants access, exposes a database exception, or changes an authentication or
authorization rejection into success.

Application audit records differ from infrastructure logs. Audit records track
the supported security actions in a stable schema; infrastructure logs describe
application/server operation. Neither should contain credentials or tokens.

## Audit retrieval API

Only an authenticated `admin` can use:

```http
GET /api/v1/audit
Authorization: Bearer <access_token>
```

Supported query parameters:

| Parameter | Meaning | Rules |
| --- | --- | --- |
| `limit` | Maximum returned records | Default 50; 1–100 |
| `offset` | Records to skip | Default 0; non-negative |
| `event_type` | Exact controlled event type | Optional |
| `user_id` | Exact positive user ID | Optional |

Records are returned newest-first, with ID as a deterministic tie-breaker.
Unauthenticated requests return 401; authenticated non-admin requests return
403 and generate an `AUTHORIZATION_DENIED` event.

No automatic retention or deletion policy is implemented. Before production,
the team should define retention duration, archival, backup protection, and
authorized deletion procedures based on deployment requirements.

## RBAC model

Supported roles are `admin`, `officer`, `worker`, and `user`. Public
registration always creates `user`; client-supplied role fields are rejected.
Policies list allowed roles explicitly rather than applying role inheritance.

- 401: authentication is missing or invalid
- 403: authentication succeeded but the role is not allowed

Role checks and authorization-denial auditing are centralized in
`require_roles(...)`.

## Architecture

```text
backend/app/
├── api/
│   ├── agent.py
│   ├── audit.py
│   ├── auth.py
│   ├── authorization.py
│   ├── dependencies.py
│   ├── health.py
│   └── router.py
├── core/
│   ├── audit.py
│   ├── config.py
│   ├── roles.py
│   └── security.py
├── db/
│   ├── audit.py
│   ├── database.py
│   └── users.py
├── schemas/
│   ├── api.py
│   ├── agent.py
│   ├── audit.py
│   ├── auth.py
│   └── authorization.py
├── services/
│   ├── api.py
│   ├── agent.py
│   ├── audit.py
│   └── auth.py
├── integrations/
│   └── agent.py
└── main.py
```

## Configuration

Configuration comes directly from environment variables. The application does
not contain a default JWT secret or load `.env` files automatically.

| Variable | Required | Default |
| --- | --- | --- |
| `COGNIVAULT_JWT_SECRET` | Required for login/token validation | None |
| `COGNIVAULT_JWT_ALGORITHM` | No | `HS256` |
| `COGNIVAULT_JWT_EXPIRATION_MINUTES` | No | `30` |
| `COGNIVAULT_DATABASE_PATH` | No | `backend/data/cognivault.db` |

Generate and export a local secret:

```bash
export COGNIVAULT_JWT_SECRET="$(openssl rand -hex 32)"
```

The `.env.example` file contains no secret. Local `.env` and SQLite database
files are ignored by Git.

## Database initialization

The default database is `backend/data/cognivault.db`. FastAPI's startup
lifespan creates the `users` and `audit_events` tables. Existing Phase 2 users
are safely assigned the default `user` role, Phase 3 databases receive the
audit table, and Phase 4 audit tables are rebuilt transactionally with the
Phase 5 agent event types while preserving records.

## Local setup and startup

```bash
cd backend
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
export COGNIVAULT_JWT_SECRET="$(openssl rand -hex 32)"
uvicorn app.main:app --reload
```

If `python3` already points to Python 3.11 or newer, it can replace
`python3.11`.

### Development worker account

Public registration intentionally creates only the basic `user` role, which
cannot execute agent tasks. For local development, an explicit provisioning
command can create a least-privileged `worker` account without changing that
policy.

From `backend/`, activate the virtual environment and run:

```bash
export COGNIVAULT_ENABLE_DEV_PROVISIONING=1
python scripts/provision_development_worker.py --username local-worker
unset COGNIVAULT_ENABLE_DEV_PROVISIONING
```

The command prompts for the password without echoing it. It uses the database
selected by `COGNIVAULT_DATABASE_PATH`, or the normal local database when that
variable is unset. It refuses duplicate usernames, never prints the password,
creates exactly the `worker` role, and writes a safe registration audit event.

For non-interactive local automation, the password may be supplied temporarily
through `COGNIVAULT_DEV_PASSWORD`. Do not put its value in a committed file or
shell history, and unset it immediately after provisioning:

```bash
read -s COGNIVAULT_DEV_PASSWORD
export COGNIVAULT_DEV_PASSWORD COGNIVAULT_ENABLE_DEV_PROVISIONING=1
python scripts/provision_development_worker.py --username local-worker
unset COGNIVAULT_DEV_PASSWORD COGNIVAULT_ENABLE_DEV_PROVISIONING
```

This command is development-only and should not be used as a production
identity-administration workflow.

Documentation is available at:

- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>
- OpenAPI JSON: <http://127.0.0.1:8000/openapi.json>

## Other API endpoints

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
- `POST /api/v1/agent/run`
- `GET /api/v1/audit`
- `GET /api/v1/authorization-demo/admin`
- `GET /api/v1/authorization-demo/operations`
- `GET /health`
- `GET /api/v1`

## Tests

Tests use fresh temporary databases and isolated JWT secrets. They do not
modify the developer database or require internet access, Ollama, GPUs, or
external APIs.

```bash
python -m pytest --rootdir=tests tests
```

The agent tests inject a fake at the adapter boundary, covering request
validation, authentication, authorization, success, safe failures, output
normalization, audit data, and the Phase 4 schema upgrade without Ollama, Qwen,
LangGraph, a GPU, network access, or model files. The explicit test root avoids
importing unrelated optional backend services.

## Planned after Phase 5

Do not infer future features from this integration boundary. Document uploads,
conversation persistence, asynchronous jobs, new RAG or vision behavior,
frontend integration, and changes to the teammate-owned agent remain outside
Phase 5. Audit retention and archival requirements also remain to be defined.

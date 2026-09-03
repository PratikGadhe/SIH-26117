# Cognivault Backend

The Cognivault backend is a local FastAPI application for the sovereign AI
workbench. Phase 4 adds structured application-level audit logging to the
existing SQLite, JWT authentication, and RBAC foundations.

## Requirements

- Python 3.11 or newer

## Implemented through Phase 4

- Versioned FastAPI routing and health checks
- SQLite user and audit persistence
- Argon2id password hashing
- Expiring JWT bearer authentication
- Explicit role-based authorization
- Security-event audit logging
- Administrator-only, filtered audit retrieval
- Safe startup upgrades for databases from earlier phases
- OpenAPI, Swagger UI, and ReDoc documentation

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
Authorization headers, request bodies, documents, prompts, model outputs, or
uploaded files. Forwarded IP headers are not trusted; only the direct peer
address supplied by the server is considered.

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
│   ├── audit.py
│   ├── auth.py
│   └── authorization.py
├── services/
│   ├── api.py
│   ├── audit.py
│   └── auth.py
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
are safely assigned the default `user` role, and Phase 3 databases receive the
new audit table without deleting or resetting user data.

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

Documentation is available at:

- Swagger UI: <http://127.0.0.1:8000/docs>
- ReDoc: <http://127.0.0.1:8000/redoc>
- OpenAPI JSON: <http://127.0.0.1:8000/openapi.json>

## Other API endpoints

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `GET /api/v1/auth/me`
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

The explicit test root avoids importing unrelated optional backend services.

## Planned after Phase 4

Retention requirements and audit coverage for real domain operations must be
designed before they are implemented. Agent execution, document access, RAG,
vision, LangGraph, model operations, and frontend audit views remain outside
Phase 4, as does a granular permission framework.

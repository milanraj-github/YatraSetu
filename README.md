# SMARTBUS — Campus Bus Tracking, Safety & Emergency Backend

> **Status:** Phase 4 Complete — Role-Based Access Control (RBAC) System.  
> *(Note: Business entities like Bus, Route, and Trips belong to future phases).*

SMARTBUS is a modern college campus transportation backend designed to support live bus tracking, passenger safety, parent-child approvals, and emergency handling across four roles: **ADMIN**, **DRIVER**, **STUDENT**, and **PARENT**.

---

## Architecture & Technology Stack

### Current Stack:
- **Language:** Python 3.11+
- **Web Framework:** FastAPI
- **ASGI Server:** Uvicorn
- **Authentication:** Firebase Authentication (Firebase ID Token verification)
- **Authorization (RBAC):** PostgreSQL `User.role` + FastAPI dependency injection (`require_role`, `require_roles`)
- **ORM:** SQLAlchemy 2.0 (Async Engine & AsyncSession)
- **Database Driver:** asyncpg
- **Database Engine:** PostgreSQL 16+
- **Migrations:** Alembic (async configuration)
- **Configuration & Validation:** Pydantic v2, Pydantic Settings, email-validator
- **Testing:** Pytest, pytest-asyncio, HTTPX

---

## Project Structure

```text
smartbus-backend/
│
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point & router mounting
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Pydantic Settings (App, DB, and Firebase)
│   │   ├── firebase.py      # Firebase Admin SDK init & token verification
│   │   └── security.py      # Auth & RBAC dependencies (require_role, require_roles)
│   │
│   ├── db/
│   │   ├── __init__.py      # DB exports (Base, engine, session factory, get_db)
│   │   ├── base.py          # SQLAlchemy 2.0 DeclarativeBase
│   │   └── database.py      # AsyncEngine & session handling
│   │
│   ├── models/
│   │   ├── __init__.py      # Model exports
│   │   ├── enums.py         # UserRole enum (ADMIN, DRIVER, STUDENT, PARENT)
│   │   └── user.py          # User entity with UUID, firebase_uid, email, role, timestamps
│   │
│   ├── schemas/
│   │   ├── __init__.py      # Schema exports
│   │   └── user.py          # User Pydantic v2 schemas + student domain validation
│   │
│   └── api/
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           ├── auth.py      # Authentication router (/api/v1/auth/me)
│           ├── health.py    # Health check routers (/api/v1/health, /api/v1/health/db)
│           └── rbac.py      # RBAC verification endpoints
│
├── alembic/
│   ├── versions/            # Database migration scripts
│   ├── env.py               # Async migration environment runner
│   ├── script.py.mako       # Migration template
│   └── README
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Async test fixtures & Windows event loop setup
│   ├── test_health.py       # Health check tests
│   ├── test_database.py     # Database connectivity & migration tests
│   ├── test_user.py         # User model, constraints & student domain tests
│   ├── test_auth.py         # Firebase auth & current-user endpoint tests
│   └── test_rbac.py         # RBAC single & multi-role permission tests
│
├── .env                     # Local secrets & configs (git-ignored)
├── .env.example             # Environment variable template
├── .gitignore               # Git ignore rules (protects credentials and secrets)
├── alembic.ini              # Alembic configuration
├── docker-compose.yml       # PostgreSQL 16 container definition
├── pytest.ini               # Pytest async configuration
├── requirements.txt         # Project dependencies
└── README.md                # Project documentation
```

---

## Authentication vs Authorization Architecture

1. **Authentication (Who you are):**
   - Verified via Firebase ID Token (`Bearer <token>`).
   - Resolves to a `firebase_uid`.
   - Client-provided roles or user IDs are never trusted as proof of identity.

2. **Authorization (What you can do):**
   - Resolved strictly from PostgreSQL `users.role`.
   - Roles: `ADMIN`, `DRIVER`, `STUDENT`, `PARENT`.
   - Enforced cleanly via FastAPI dependencies:
     - `require_role(UserRole.ADMIN)`
     - `require_roles(UserRole.ADMIN, UserRole.DRIVER)`
   - Missing/invalid authentication $\rightarrow$ `HTTP 401 Unauthorized`.
   - Insufficient permissions $\rightarrow$ `HTTP 403 Forbidden`.

---

## API Endpoints & Interactive Docs

| Endpoint | Method | Access Level | Description |
| :--- | :--- | :--- | :--- |
| `/` | `GET` | Public | Root welcome message |
| `/api/v1/health` | `GET` | Public | Service operational health check |
| `/api/v1/health/db` | `GET` | Public | PostgreSQL connectivity health check |
| `/api/v1/auth/me` | `GET` | Authenticated | Current user profile |
| `/api/v1/rbac/admin-test` | `GET` | `ADMIN` only | Admin RBAC verification |
| `/api/v1/rbac/driver-test` | `GET` | `DRIVER` only | Driver RBAC verification |
| `/api/v1/rbac/student-test` | `GET` | `STUDENT` only | Student RBAC verification |
| `/api/v1/rbac/parent-test` | `GET` | `PARENT` only | Parent RBAC verification |
| `/api/v1/rbac/admin-driver-test` | `GET` | `ADMIN` or `DRIVER` | Shared multi-role RBAC verification |
| `/docs` | `GET` | Public | Interactive Swagger UI documentation |
| `/redoc` | `GET` | Public | Interactive ReDoc documentation |
| `/openapi.json` | `GET` | Public | OpenAPI 3.0 schema |

---

## Running Automated Tests

```bash
pytest -v
```

# SMARTBUS — Campus Bus Tracking, Safety & Emergency Backend

> **Status:** Phase 5 Complete — Bus Management Module.  
> *(Note: Routes, Stops, and Driver Assignment belong to future phases).*

SMARTBUS is a modern college campus transportation backend designed to support live bus tracking, passenger safety, parent-child approvals, and emergency handling across four roles: **ADMIN**, **DRIVER**, **STUDENT**, and **PARENT**.

---

## Architecture & Technology Stack

### Current Stack:
- **Language:** Python 3.11+
- **Web Framework:** FastAPI
- **ASGI Server:** Uvicorn
- **Authentication:** Firebase Authentication (Firebase ID Token verification)
- **Authorization (RBAC):** PostgreSQL `User.role` + FastAPI dependency injection (`require_role(UserRole.ADMIN)`)
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
│   ├── main.py              # FastAPI entry point & router registration
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
│   │   ├── user.py          # User entity (assigned_bus_id foreign key)
│   │   └── bus.py           # Bus entity (bus_number, registration_number, capacity)
│   │
│   ├── schemas/
│   │   ├── __init__.py      # Schema exports
│   │   ├── user.py          # User Pydantic v2 schemas + student domain validation
│   │   └── bus.py           # Bus Pydantic v2 schemas (Create, Update, Response)
│   │
│   ├── services/
│   │   ├── __init__.py      # Service layer exports
│   │   └── bus_service.py   # Bus CRUD operations and uniqueness conflict checks
│   │
│   └── api/
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           ├── auth.py      # Authentication router (/api/v1/auth/me)
│           ├── health.py    # Health check routers (/api/v1/health, /api/v1/health/db)
│           ├── rbac.py      # RBAC verification endpoints
│           └── buses.py     # Bus management CRUD API (/api/v1/buses)
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
│   ├── test_rbac.py         # RBAC single & multi-role permission tests
│   └── test_buses.py        # Bus model, validation, CRUD, and safe deactivation tests
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

## Bus Management Module (Phase 5)

### 1. Database Model & Relationship
- **`buses` table:**
  - `id`: UUID (Primary Key)
  - `bus_number`: String(50), Unique, Indexed, Non-null
  - `registration_number`: String(50), Unique, Indexed, Non-null
  - `capacity`: Integer, Positive (`CHECK (capacity > 0)`)
  - `is_active`: Boolean, default `true`
  - `created_at`, `updated_at`: Timezone-aware Timestamps
- **`User <-> Bus` Relationship:**
  - `users.assigned_bus_id`: UUID Foreign Key referencing `buses.id` (`ON DELETE SET NULL`), enabling driver assignment in later phases.

### 2. RBAC & Access Control
- All Bus CRUD endpoints are strictly restricted to users with the **`ADMIN`** role.
- Deletions are implemented as **safe soft deactivations** (`is_active = false`) to preserve data integrity for historical records.

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
| `/api/v1/buses` | `POST` | `ADMIN` only | Create a new bus |
| `/api/v1/buses` | `GET` | `ADMIN` only | List buses with pagination |
| `/api/v1/buses/{bus_id}` | `GET` | `ADMIN` only | Retrieve bus details by ID |
| `/api/v1/buses/{bus_id}` | `PATCH` | `ADMIN` only | Update bus details |
| `/api/v1/buses/{bus_id}` | `DELETE` | `ADMIN` only | Safely deactivate bus (`is_active = false`) |
| `/docs` | `GET` | Public | Interactive Swagger UI documentation |
| `/redoc` | `GET` | Public | Interactive ReDoc documentation |
| `/openapi.json` | `GET` | Public | OpenAPI 3.0 schema |

---

## Running Automated Tests

```bash
pytest -v
```

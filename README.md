# SMARTBUS — Campus Bus Tracking, Safety & Emergency Backend

> **Status:** Phase 3 Complete — User Model + Firebase Authentication Foundation.  
> *(Note: Full RBAC authorization and role-based route access controls belong to Phase 4).*

SMARTBUS is a modern college campus transportation backend designed to support live bus tracking, passenger safety, parent-child approvals, and emergency handling across four roles: **ADMIN**, **DRIVER**, **STUDENT**, and **PARENT**.

---

## Architecture & Technology Stack

### Phase 1, 2 & 3 Completed Stack:
- **Language:** Python 3.11+
- **Web Framework:** FastAPI
- **ASGI Server:** Uvicorn
- **Authentication:** Firebase Authentication (Firebase Admin SDK token verification)
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
│   │   ├── firebase.py      # Firebase Admin SDK init & ID token verification
│   │   └── security.py      # Bearer auth & get_current_user dependencies
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
│           └── health.py    # Health check routers (/api/v1/health, /api/v1/health/db)
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
│   └── test_auth.py         # Firebase auth & current-user endpoint tests
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

## Identity & Authentication Architecture

### 1. Separation of Responsibilities
- **Firebase Authentication:** Handles user identity credentials (email/password, OAuth logins, token issuance, password resets). Passwords and private credentials are never stored in the SMARTBUS database.
- **SMARTBUS PostgreSQL (`users` table):** Stores application-level profile data (`id` (UUID), `firebase_uid` (indexed/unique), `email` (indexed/unique), `full_name`, `role`, `created_at`, `updated_at`).

### 2. Student Domain Requirement
- `STUDENT` accounts must use the college domain: `@sode-edu.in` (case-insensitive).
- Non-student roles (`ADMIN`, `DRIVER`, `PARENT`) are not restricted to this domain.

---

## Getting Started

### 1. Prerequisites
- Python 3.11+
- PostgreSQL 16+ running locally OR Docker Desktop.
- Git installed.

### 2. Virtual Environment & Dependencies

```bash
python -m venv .venv
.\.venv\Scripts\Activate.ps1   # On Windows
# or source .venv/bin/activate # On Linux/macOS

pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Environment Configuration

Copy `.env.example` to `.env`:
```env
APP_NAME=SMARTBUS Backend
APP_VERSION=0.1.0
ENVIRONMENT=development
DEBUG=true

POSTGRES_USER=smartbus_user
POSTGRES_PASSWORD=smartbus_password
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=smartbus_db
DATABASE_URL=postgresql+asyncpg://smartbus_user:smartbus_password@localhost:5432/smartbus_db

# Firebase Authentication (Optional in local dev/mocked in tests)
FIREBASE_CREDENTIALS_PATH=
FIREBASE_PROJECT_ID=smartbus-campus
```

### 4. Run Migrations

```bash
alembic upgrade head
```

### 5. Start Server

```bash
uvicorn app.main:app --reload
```

---

## API Endpoints & Interactive Docs

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Root welcome message |
| `/api/v1/health` | `GET` | Service operational health check |
| `/api/v1/health/db` | `GET` | Database connectivity health check (`SELECT 1`) |
| `/api/v1/auth/me` | `GET` | Authenticated user profile (requires `Bearer <firebase_id_token>`) |
| `/docs` | `GET` | Interactive Swagger UI documentation |
| `/redoc` | `GET` | Interactive ReDoc documentation |
| `/openapi.json` | `GET` | OpenAPI 3.0 JSON schema |

---

## Running Automated Tests

```bash
pytest -v
```

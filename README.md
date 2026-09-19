# SMARTBUS — Campus Bus Tracking, Safety & Emergency Backend

> **Status:** Phase 2 Complete — PostgreSQL + SQLAlchemy 2.0 Async + Alembic Database Foundation.  
> *(Note: Business database models are NOT implemented yet. Only database connectivity & migration infrastructure are established).*

SMARTBUS is a modern college campus transportation backend designed to support live bus tracking, passenger safety, parent-child approvals, and emergency handling across four roles: **Admin**, **Driver**, **Student**, and **Parent**.

---

## Architecture & Technology Stack

### Phase 1 & 2 Completed Stack:
- **Language:** Python 3.11+
- **Web Framework:** FastAPI
- **ASGI Server:** Uvicorn
- **ORM:** SQLAlchemy 2.0 (Async Engine & AsyncSession)
- **Database Driver:** asyncpg
- **Database Engine:** PostgreSQL 16+
- **Migrations:** Alembic (configured for async SQLAlchemy)
- **Configuration & Validation:** Pydantic v2 & Pydantic Settings
- **Testing:** Pytest, pytest-asyncio, HTTPX

---

## Project Structure

```text
smartbus-backend/
│
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   └── config.py        # Pydantic v2 Settings (App & DB configs)
│   │
│   ├── db/
│   │   ├── __init__.py      # DB package exports
│   │   ├── base.py          # SQLAlchemy 2.0 DeclarativeBase (Base)
│   │   └── database.py      # AsyncEngine, async_sessionmaker, get_db dependency
│   │
│   └── api/
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           └── health.py    # Health routers (/api/v1/health, /api/v1/health/db)
│
├── alembic/
│   ├── versions/            # Migration versions directory
│   ├── env.py               # Async migration environment runner
│   ├── script.py.mako       # Migration template
│   └── README
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest async client & DB pool cleanup fixtures
│   ├── test_health.py       # Root & API health tests
│   └── test_database.py     # Database connectivity & Alembic tests
│
├── .env                     # Local development environment secrets (git-ignored)
├── .env.example             # Environment variable template
├── .gitignore               # Git ignore rules
├── alembic.ini              # Alembic configuration file
├── docker-compose.yml       # PostgreSQL 16 container definition
├── pytest.ini               # Pytest async configuration
├── requirements.txt         # Project dependencies
└── README.md                # Project documentation
```

---

## Getting Started

### 1. Prerequisites
- Python 3.11 or higher installed.
- PostgreSQL 16+ installed locally OR Docker Desktop.
- Git installed.

---

### 2. Create and Activate a Virtual Environment

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**On Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 4. Configure Environment Variables

Copy `.env.example` to `.env` if not already present:

**Windows:**
```powershell
copy .env.example .env
```

**Linux / macOS:**
```bash
cp .env.example .env
```

Default variables in `.env`:
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
```

---

### 5. Running PostgreSQL

#### Option A: Using Docker Compose
```bash
docker compose up -d
```
To verify container status:
```bash
docker compose ps
```

#### Option B: Using Local PostgreSQL Service
Ensure PostgreSQL service is running on port 5432 and database `smartbus_db` is created for `smartbus_user`.

---

### 6. Database Migrations with Alembic

Run pending migrations to the latest head:
```bash
alembic upgrade head
```

To create a new migration revision (in future phases):
```bash
alembic revision --autogenerate -m "migration_name"
```

---

### 7. Running the FastAPI Server

Start Uvicorn with live reload:
```bash
uvicorn app.main:app --reload
```

The server will be available at `http://127.0.0.1:8000`.

---

## API Endpoints & Interactive Docs

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Root welcome message |
| `/api/v1/health` | `GET` | Service operational health check |
| `/api/v1/health/db` | `GET` | PostgreSQL connectivity health check (`SELECT 1`) |
| `/docs` | `GET` | Interactive Swagger UI documentation |
| `/redoc` | `GET` | Interactive ReDoc documentation |
| `/openapi.json` | `GET` | OpenAPI 3.0 schema |

---

## Running Automated Tests

Run the test suite using Pytest:
```bash
pytest -v
```

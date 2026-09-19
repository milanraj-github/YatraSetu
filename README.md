# SMARTBUS — Campus Bus Tracking, Safety & Emergency Backend

> **Status:** Phase 6 Complete — Route Management, Boarding Points & Stop Sequencing.  
> *(Note: Driver assignment, Live Trips, and GPS Ingestion belong to future phases).*

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
│   │   ├── bus.py           # Bus entity
│   │   ├── route.py         # Route entity (code, name, description)
│   │   ├── boarding_point.py# BoardingPoint entity (coordinates & address)
│   │   └── route_stop.py    # RouteStop association model (ordered stops)
│   │
│   ├── schemas/
│   │   ├── __init__.py      # Schema exports
│   │   ├── user.py          # User schemas + student domain validation
│   │   ├── bus.py           # Bus schemas
│   │   ├── route.py         # Route schemas
│   │   ├── boarding_point.py# BoardingPoint schemas (latitude/longitude checks)
│   │   └── route_stop.py    # RouteStop schemas (ordering & offset)
│   │
│   ├── services/
│   │   ├── __init__.py      # Service layer exports
│   │   ├── bus_service.py   # Bus CRUD operations
│   │   ├── route_service.py # Route CRUD operations
│   │   ├── boarding_point_service.py # Boarding point operations
│   │   └── route_stop_service.py     # Stop sequencing and safe reordering
│   │
│   └── api/
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           ├── auth.py            # Authentication router (/api/v1/auth/me)
│           ├── health.py          # Health check routers (/api/v1/health, /api/v1/health/db)
│           ├── rbac.py            # RBAC verification endpoints
│           ├── buses.py           # Bus management CRUD API (/api/v1/buses)
│           ├── routes.py          # Routes & Route Stops API (/api/v1/routes)
│           └── boarding_points.py # Boarding Points API (/api/v1/boarding-points)
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
│   ├── test_buses.py        # Bus model, validation, CRUD, and safe deactivation tests
│   ├── test_routes.py       # Route model, uniqueness, and CRUD tests
│   ├── test_boarding_points.py # Boarding point coordinates & CRUD tests
│   └── test_route_stops.py  # Route-stop sequencing & 2-phase reordering tests
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

## Route Management, Boarding Points & Sequencing (Phase 6)

### 1. Database Entities & Constraints
- **`routes` Table:**
  - `id`: UUID (Primary Key)
  - `name`: String(100), Non-null
  - `code`: String(50), Unique, Indexed, Non-null
  - `description`: String(255), Nullable
  - `is_active`: Boolean, default `true`
  - `created_at`, `updated_at`: Timezone-aware Timestamps
- **`boarding_points` Table:**
  - `id`: UUID (Primary Key)
  - `name`: String(100), Non-null
  - `latitude`: Float, Check (`-90.0 <= latitude <= 90.0`)
  - `longitude`: Float, Check (`-180.0 <= longitude <= 180.0`)
  - `address`: String(255), Nullable
  - `is_active`: Boolean, default `true`
- **`route_stops` Association Table:**
  - `id`: UUID (Primary Key)
  - `route_id`: Foreign Key $\rightarrow$ `routes.id` (`ON DELETE CASCADE`)
  - `boarding_point_id`: Foreign Key $\rightarrow$ `boarding_points.id` (`ON DELETE RESTRICT`)
  - `stop_order`: Integer, Positive (`CHECK (stop_order > 0)`)
  - `scheduled_arrival_offset_minutes`: Integer, Non-negative (`CHECK (scheduled_arrival_offset_minutes >= 0)`)
  - Unique Constraint: `(route_id, stop_order)`
  - Unique Constraint: `(route_id, boarding_point_id)`

### 2. Stop Reordering Algorithm
- Safe two-phase database update strategy prevents transient unique constraint violations when shifting sequence orders.

---

## API Endpoints & Interactive Docs

| Endpoint | Method | Access Level | Description |
| :--- | :--- | :--- | :--- |
| `/` | `GET` | Public | Root welcome message |
| `/api/v1/health` | `GET` | Public | Service operational health check |
| `/api/v1/health/db` | `GET` | Public | PostgreSQL connectivity health check |
| `/api/v1/auth/me` | `GET` | Authenticated | Current user profile |
| `/api/v1/rbac/*` | `GET` | RBAC Protected | RBAC role verification endpoints |
| `/api/v1/buses` | `POST`, `GET` | `ADMIN` only | Bus registration and list |
| `/api/v1/buses/{id}` | `GET`, `PATCH`, `DELETE` | `ADMIN` only | Bus details, update, soft deactivation |
| `/api/v1/routes` | `POST`, `GET` | `ADMIN` only | Route creation and list |
| `/api/v1/routes/{id}` | `GET`, `PATCH`, `DELETE` | `ADMIN` only | Route details, update, soft deactivation |
| `/api/v1/boarding-points` | `POST`, `GET` | `ADMIN` only | Boarding point creation and list |
| `/api/v1/boarding-points/{id}`| `GET`, `PATCH`, `DELETE` | `ADMIN` only | Boarding point details, update, soft deactivation |
| `/api/v1/routes/{id}/stops` | `POST`, `GET` | `ADMIN` only | Add stop to route & list ordered stops |
| `/api/v1/routes/{id}/stops/{sid}` | `PATCH`, `DELETE` | `ADMIN` only | Update stop offset & remove stop |
| `/api/v1/routes/{id}/stops/{sid}/order` | `PATCH` | `ADMIN` only | Safely reorder stop sequence |
| `/docs` | `GET` | Public | Interactive Swagger UI documentation |
| `/redoc` | `GET` | Public | Interactive ReDoc documentation |
| `/openapi.json` | `GET` | Public | OpenAPI 3.0 schema |

---

## Running Automated Tests

```bash
pytest -v
```

# SMARTBUS — Campus Bus Tracking, Safety & Emergency Backend

> **Status:** Phase 8 Complete — GPS Ingestion & Historical Telemetry Persistence.  
> *(Note: Redis, WebSockets, PostGIS, Geofencing, ETA, and Emergency systems belong to future phases).*

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
│   │   ├── enums.py         # UserRole & TripStatus enums
│   │   ├── user.py          # User entity (assigned_bus_id foreign key)
│   │   ├── bus.py           # Bus entity
│   │   ├── route.py         # Route entity (code, name, description)
│   │   ├── boarding_point.py# BoardingPoint entity (coordinates & address)
│   │   ├── route_stop.py    # RouteStop association model (ordered stops)
│   │   ├── trip.py          # Trip entity (route, bus, driver, lifecycle status)
│   │   └── location.py      # LocationPing entity (GPS telemetry & coordinates)
│   │
│   ├── schemas/
│   │   ├── __init__.py      # Schema exports
│   │   ├── user.py          # User schemas + student domain validation
│   │   ├── bus.py           # Bus schemas
│   │   ├── route.py         # Route schemas
│   │   ├── boarding_point.py# BoardingPoint schemas (latitude/longitude checks)
│   │   ├── route_stop.py    # RouteStop schemas (ordering & offset)
│   │   ├── driver.py        # Driver assignment schemas
│   │   ├── trip.py          # Trip creation & response schemas
│   │   └── gps.py           # GPS LocationPing creation & response schemas
│   │
│   ├── services/
│   │   ├── __init__.py      # Service layer exports
│   │   ├── bus_service.py   # Bus CRUD operations
│   │   ├── route_service.py # Route CRUD operations
│   │   ├── boarding_point_service.py # Boarding point operations
│   │   ├── route_stop_service.py     # Stop sequencing and safe reordering
│   │   ├── driver_service.py         # Driver bus assignment & verification
│   │   ├── trip_service.py           # Trip lifecycle & driver ownership
│   │   └── gps_service.py            # GPS ingestion & historical query service
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
│           ├── boarding_points.py # Boarding Points API (/api/v1/boarding-points)
│           ├── drivers.py         # Driver bus assignment API (/api/v1/drivers)
│           ├── trips.py           # Trip management & lifecycle API (/api/v1/trips)
│           └── gps.py             # GPS Ingestion & History API (/api/v1/trips/{id}/gps)
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
│   ├── test_route_stops.py  # Route-stop sequencing & 2-phase reordering tests
│   ├── test_drivers.py      # Driver assignment and unassignment tests
│   ├── test_trips.py        # Trip creation, driver ownership, and lifecycle tests
│   └── test_gps.py          # GPS ingestion, validation, out-of-order & duplicate retention tests
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

## GPS Ingestion & Telemetry (Phase 8)

### 1. Database Model & Constraints
- **`location_pings` Table:**
  - `id`: UUID (Primary Key)
  - `trip_id`: Foreign Key $\rightarrow$ `trips.id` (`ON DELETE RESTRICT`)
  - `driver_id`: Foreign Key $\rightarrow$ `users.id` (`ON DELETE RESTRICT`)
  - `latitude`: Float with Check (`-90.0 <= latitude <= 90.0`)
  - `longitude`: Float with Check (`-180.0 <= longitude <= 180.0`)
  - `recorded_at`: Timezone-aware Timestamp (Device timestamp)
  - `received_at`: Timezone-aware Timestamp (Server-generated ingestion timestamp)
  - `accuracy_meters`: Float, Check (`accuracy_meters IS NULL OR accuracy_meters >= 0`)
  - `speed_mps`: Float, Check (`speed_mps IS NULL OR speed_mps >= 0`)
  - `heading_degrees`: Float, Check (`heading_degrees IS NULL OR (heading_degrees >= 0 AND heading_degrees < 360)`)
  - `created_at`: Timezone-aware Timestamp
  - Composite Index: `(trip_id, recorded_at)`

### 2. Driver Ownership & Ingestion Rules
- **Driver Role Enforcement:** Only authenticated `DRIVER` users may submit GPS telemetry. Admins, students, and parents cannot submit GPS points.
- **Ownership Verification:** The authenticated driver must be assigned to the trip (`trip.driver_id == current_user.id`) and currently assigned to that trip's bus (`trip.bus_id == current_user.assigned_bus_id`).
- **Trip Status Requirement:** GPS points are accepted only when `trip.status == TripStatus.IN_PROGRESS`. Attempts to submit GPS for `SCHEDULED`, `COMPLETED`, or `CANCELLED` trips return `409 Conflict`.
- **Server Timestamps:** `received_at` is generated securely on the server. Clients cannot spoof `received_at`.
- **Out-of-Order & Duplicate Retention:** Out-of-order and duplicate GPS points are persisted without deletion or overwriting to maintain comprehensive audit history. Historical queries order points by `recorded_at ASC, received_at ASC, id ASC`.

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
| `/api/v1/drivers/{driver_id}/assign-bus/{bus_id}` | `POST` | `ADMIN` only | Assign bus to driver |
| `/api/v1/drivers/{driver_id}/unassign-bus` | `DELETE` | `ADMIN` only | Unassign bus from driver |
| `/api/v1/drivers/{driver_id}/assignment` | `GET` | `ADMIN` or `DRIVER` (self) | View driver's bus assignment |
| `/api/v1/trips` | `POST` | `ADMIN` only | Schedule a new trip |
| `/api/v1/trips` | `GET` | `ADMIN` (all), `DRIVER` (own) | List trips |
| `/api/v1/trips/{id}` | `GET` | `ADMIN` (all), `DRIVER` (own) | Get trip details |
| `/api/v1/trips/{id}/start` | `POST` | `ADMIN` or Assigned `DRIVER` | Start a scheduled trip |
| `/api/v1/trips/{id}/end` | `POST` | `ADMIN` or Assigned `DRIVER` | End an in-progress trip |
| `/api/v1/trips/{id}/cancel` | `POST` | `ADMIN` only | Cancel a scheduled trip |
| `/api/v1/trips/{trip_id}/gps` | `POST` | Assigned `DRIVER` only | Ingest GPS location telemetry |
| `/api/v1/trips/{trip_id}/gps` | `GET` | `ADMIN` or Assigned `DRIVER` | Retrieve chronological GPS history |
| `/docs` | `GET` | Public | Interactive Swagger UI documentation |
| `/redoc` | `GET` | Public | Interactive ReDoc documentation |
| `/openapi.json` | `GET` | Public | OpenAPI 3.0 schema |

---

## Running Automated Tests

```bash
pytest -v
```

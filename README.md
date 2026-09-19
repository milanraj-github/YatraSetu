# SMARTBUS — Campus Bus Tracking, Safety & Emergency Backend

> **Status:** Phase 9 Complete — Redis-Backed Live Location State & Monotonic Telemetry Tracking.  
> *(Note: WebSockets, PostGIS, Geofencing, ETA, Notifications, and Emergency systems belong to future phases).*

SMARTBUS is a modern college campus transportation backend designed to support live bus tracking, passenger safety, parent-child approvals, and emergency handling across four roles: **ADMIN**, **DRIVER**, **STUDENT**, and **PARENT**.

---

## Architecture & Technology Stack

### Current Stack:
- **Language:** Python 3.11+
- **Web Framework:** FastAPI
- **ASGI Server:** Uvicorn
- **In-Memory Cache / State:** Redis 7.2 (`redis.asyncio` with connection pooling & Lua atomic scripts)
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
│   │   ├── config.py        # Pydantic Settings (App, DB, Redis, and Firebase)
│   │   ├── firebase.py      # Firebase Admin SDK init & token verification
│   │   ├── redis.py         # Redis async connection pool & lifecycle management
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
│   │   └── gps.py           # GPS LocationPing & LiveLocationResponse schemas
│   │
│   ├── services/
│   │   ├── __init__.py      # Service layer exports
│   │   ├── bus_service.py   # Bus CRUD operations
│   │   ├── route_service.py # Route CRUD operations
│   │   ├── boarding_point_service.py # Boarding point operations
│   │   ├── route_stop_service.py     # Stop sequencing and safe reordering
│   │   ├── driver_service.py         # Driver bus assignment & verification
│   │   ├── trip_service.py           # Trip lifecycle & driver ownership
│   │   └── gps_service.py            # GPS ingestion, Redis live location & history
│   │
│   └── api/
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           ├── auth.py            # Authentication router (/api/v1/auth/me)
│           ├── health.py          # Health check routers (/health, /health/db, /health/redis)
│           ├── rbac.py            # RBAC verification endpoints
│           ├── buses.py           # Bus management CRUD API (/api/v1/buses)
│           ├── routes.py          # Routes & Route Stops API (/api/v1/routes)
│           ├── boarding_points.py # Boarding Points API (/api/v1/boarding-points)
│           ├── drivers.py         # Driver bus assignment API (/api/v1/drivers)
│           ├── trips.py           # Trip management & lifecycle API (/api/v1/trips)
│           └── gps.py             # GPS Ingestion, History & Live Location API
│
├── alembic/
│   ├── versions/            # Database migration scripts
│   ├── env.py               # Async migration environment runner
│   ├── script.py.mako       # Migration template
│   └── README
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Async test fixtures, Windows event loop & in-memory Redis mock
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
│   ├── test_gps.py          # GPS ingestion, validation, out-of-order & duplicate retention tests
│   └── test_redis.py        # Redis health, monotonic live location updates, fault tolerance & cleanup tests
│
├── .env                     # Local secrets & configs (git-ignored)
├── .env.example             # Environment variable template
├── .gitignore               # Git ignore rules (protects credentials and secrets)
├── alembic.ini              # Alembic configuration
├── docker-compose.yml       # PostgreSQL 16 & Redis 7.2 container definitions
├── pytest.ini               # Pytest async configuration
├── requirements.txt         # Project dependencies
└── README.md                # Project documentation
```

---

## Redis + Live Location Architecture (Phase 9)

### 1. Dual-Store Strategy
```text
Driver GPS Request
       │
       ├──► PostgreSQL (LocationPing) ──► Historical audit trail (stores ALL valid points)
       │
       └──► Redis (smartbus:trip:{id}:live) ──► Latest live location pointer (monotonic)
```

### 2. Monotonic Live Location Guarantee
- **Lua Script Atomicity:** Redis live location updates are executed using a Lua script that performs atomic compare-and-set based on `recorded_at` (device capture timestamp).
- **Out-of-Order Handling:** Older GPS points arriving late are persisted to PostgreSQL for historical completeness but will **never** move the Redis live location pointer backwards in time.
- **Key Format:** `smartbus:trip:{trip_id}:live`
- **Stored Payload:**
  ```json
  {
    "trip_id": "...",
    "driver_id": "...",
    "bus_id": "...",
    "latitude": 13.3409,
    "longitude": 74.7421,
    "recorded_at": "2026-09-19T10:05:00+00:00",
    "received_at": "2026-09-19T10:05:00.123456+00:00",
    "accuracy_meters": 5.0,
    "speed_mps": 8.5,
    "heading_degrees": 120.0,
    "recorded_at_epoch": 1789812300.0
  }
  ```

### 3. Fault-Tolerance & Lifecycle Cleanup
- **Fault-Tolerant Ingestion:** If Redis is temporarily unavailable or encounters an error, the PostgreSQL write remains committed, the point is preserved, and the GPS ingestion endpoint returns `201 Created`.
- **Trip Lifecycle Cleanup:** When a trip transitions to `COMPLETED` (`POST /api/v1/trips/{id}/end`) or `CANCELLED` (`POST /api/v1/trips/{id}/cancel`), the Redis live location key is automatically deleted to prevent stale state.

---

## API Endpoints & Interactive Docs

| Endpoint | Method | Access Level | Description |
| :--- | :--- | :--- | :--- |
| `/` | `GET` | Public | Root welcome message |
| `/api/v1/health` | `GET` | Public | Service operational health check |
| `/api/v1/health/db` | `GET` | Public | PostgreSQL connectivity health check |
| `/api/v1/health/redis` | `GET` | Public | Redis server connectivity health check |
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
| `/api/v1/trips/{id}/end` | `POST` | `ADMIN` or Assigned `DRIVER` | End an in-progress trip & clean live cache |
| `/api/v1/trips/{id}/cancel` | `POST` | `ADMIN` only | Cancel a scheduled trip & clean live cache |
| `/api/v1/trips/{trip_id}/gps` | `POST` | Assigned `DRIVER` only | Ingest GPS location telemetry |
| `/api/v1/trips/{trip_id}/gps` | `GET` | `ADMIN` or Assigned `DRIVER` | Retrieve chronological GPS history |
| `/api/v1/trips/{trip_id}/live` | `GET` | `ADMIN` or Assigned `DRIVER` | Retrieve latest cached live location |
| `/docs` | `GET` | Public | Interactive Swagger UI documentation |
| `/redoc` | `GET` | Public | Interactive ReDoc documentation |
| `/openapi.json` | `GET` | Public | OpenAPI 3.0 schema |

---

## Running Automated Tests

```bash
pytest -v
```

# SMARTBUS — Campus Bus Tracking, Safety & Emergency Backend

> **Status:** Phase 14 Complete — Basic ETA Engine.  
> *(Note: Baseline deterministic ETA calculation using PostGIS ST_Distance and configurable average speed complete. FCM, Email, Notifications, and Emergency/SOS belong to future phases).*




SMARTBUS is a modern college campus transportation backend designed to support live bus tracking, passenger safety, parent-child approvals, and emergency handling across four roles: **ADMIN**, **DRIVER**, **STUDENT**, and **PARENT**.

---

## Architecture & Technology Stack

### Current Stack:
- **Language:** Python 3.11+
- **Web Framework:** FastAPI (REST + WebSockets)
- **ASGI Server:** Uvicorn
- **In-Memory Cache & Pub/Sub:** Redis 7.2 (`redis.asyncio` with connection pooling, Pub/Sub & Lua atomic scripts)
- **Authentication:** Firebase Authentication (Firebase ID Token verification over HTTP and WebSockets)
- **Authorization (RBAC):** PostgreSQL `User.role` + FastAPI dependency injection (`require_role`, `require_roles`, `get_websocket_user`)
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
│   │   └── security.py      # Auth & RBAC dependencies (require_role, require_roles, get_websocket_user)
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
│   │   ├── gps_service.py            # GPS ingestion, Redis live location & history
│   │   └── websocket_manager.py      # WebSocket connection & Redis Pub/Sub manager
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
│           ├── gps.py             # GPS Ingestion, History & Live Location API
│           └── ws.py              # Realtime WebSocket telemetry streaming (/ws/trips/{id})
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
│   ├── test_redis.py        # Redis health, monotonic live location updates & cleanup tests
│   └── test_websocket.py    # WebSocket auth, RBAC, initial state, monotonic live streaming & multi-client tests
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

## Realtime WebSocket Telemetry Architecture (Phase 10)

```text
Driver GPS Request
       │
       ├──► PostgreSQL (LocationPing) ──► Complete historical audit log
       │
       └──► Redis (SET smartbus:trip:{id}:live & PUBLISH smartbus:trip:{id}:location)
                    │
                    ▼ (Pub/Sub Broadcast)
             WebSocketManager
                    │
                    ├──► Admin Web Dashboard (WS)
                    ├──► Assigned Driver App (WS)
                    └──► (Future Student / Parent Subscribers)
```

### 1. Atomic Monotonic Lua Update + Pub/Sub
- **Atomic Compare-and-Publish:** GPS updates run an atomic Lua script that compares `recorded_at_epoch`. If the incoming point is newer/equal:
  - Updates live key: `smartbus:trip:{trip_id}:live`
  - Publishes payload on: `smartbus:trip:{trip_id}:location`
  - Returns `1`
- **Out-of-Order Guarantee:** Older points arriving late are saved to PostgreSQL but are **never** published over WebSockets or stored in Redis live state.

### 2. Connection Lifecycle & Initial State
- **Endpoint:** `WS /api/v1/ws/trips/{trip_id}`
- **Authentication:** Token via `Authorization: Bearer <token>` header or `?token=<token>` query param.
- **Authorization:** `ADMIN` or assigned `DRIVER` (`trip.driver_id == current_user.id` and `trip.bus_id == current_user.assigned_bus_id`).
- **Initial State Delivery:** When a client connects:
  - If Redis already has live state, sends current live location JSON immediately.
  - If no GPS points ingested yet, sends `{"type": "connected", "trip_id": "<id>"}`.
- **Trip Lifecycle Enforcement:** Connections to `COMPLETED` or `CANCELLED` trips are rejected with policy close code `1008`. When a trip ends, a `{"type": "trip_ended"}` message is broadcast and Redis state is deleted.

---

## API Endpoints & Interactive Docs

| Endpoint | Method / Protocol | Access Level | Description |
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
| `/api/v1/trips/{trip_id}/eta` | `GET` | Authenticated (RBAC protected) | Calculate baseline arrival time estimates for all route stops |
| `/api/v1/trips/{trip_id}/gps` | `POST` | Assigned `DRIVER` only | Ingest single GPS location telemetry |
| `/api/v1/trips/{trip_id}/gps/sync` | `POST` | Assigned `DRIVER` only | Ingest batch of offline-queued GPS points (1-500) with idempotency |
| `/api/v1/trips/{trip_id}/gps` | `GET` | `ADMIN` or Assigned `DRIVER` | Retrieve chronological GPS history |
| `/api/v1/trips/{trip_id}/live` | `GET` | `ADMIN` or Assigned `DRIVER` | Retrieve latest cached live location |
| `/api/v1/ws/trips/{trip_id}` | `WebSocket` | `ADMIN` or Assigned `DRIVER` | Realtime live location telemetry stream |
| `/api/v1/auth/register-parent` | `POST` | Authenticated | Register parent account and initiate student link |
| `/api/v1/parent-links` | `GET` | `STUDENT` only | List student's received parent link requests |
| `/api/v1/parent-links/{id}/approve` | `POST` | `STUDENT` only | Approve pending parent link request |
| `/api/v1/parent-links/{id}/reject` | `POST` | `STUDENT` only | Reject pending parent link request |
| `/api/v1/parent/children` | `GET` | `PARENT` only | List approved linked children |
| `/api/v1/parent/children/{id}/live` | `GET` | `PARENT` only | Track active bus live location for approved child |
| `/docs` | `GET` | Public | Interactive Swagger UI documentation |
| `/redoc` | `GET` | Public | Interactive ReDoc documentation |
| `/openapi.json` | `GET` | Public | OpenAPI 3.0 schema |

---

## Basic ETA Engine (Phase 14)

```text
Current Bus Live Position (lat, lon from Redis)
       │
       ├──► Query ordered RouteStops + BoardingPoints (ORDER BY stop_order ASC)
       │
       ├──► PostGIS ST_Distance(current_point, stop_location) -> distance_meters
       │
       ├──► ETA Calculation: eta_seconds = distance_meters / DEFAULT_ETA_SPEED_MPS
       │
       └──► Output: estimated_arrival_at = generated_at + timedelta(seconds=eta_seconds)
```

- **Deterministic Baseline Algorithm:** Computes travel times based on geodesic distance from current bus position to each route stop:
  $$\text{ETA (seconds)} = \frac{\text{Distance (meters)}}{\text{DEFAULT\_ETA\_SPEED\_MPS}}$$
- **Configurable Speed Parameter:** Baseline speed configured via `DEFAULT_ETA_SPEED_MPS = 8.0` (~28.8 km/h) in `Settings` with strict positive validation (`> 0.0`).
- **Authorization Enforcements:**
  - `ADMIN`: Allowed for all trips.
  - `DRIVER`: Allowed only for their own assigned trip.
  - `PARENT`: Allowed only if having an approved relationship with a student assigned to the operating bus.
  - `STUDENT`: Allowed only if assigned to the operating bus.
- **Trip Lifecycle Enforcement:** ETA calculations require the trip to be `IN_PROGRESS` (returns `409 Conflict` if `SCHEDULED`, `COMPLETED`, or `CANCELLED`).
- **Technical Limitations & Scope:**
  - **Baseline deterministic estimation** — provides predictable travel time approximations based on straight-line spatial distance.
  - **No traffic or road-network graph routing** — does not incorporate OSM turn-by-turn road network geometry or live traffic telemetry.
  - **No ML / AI prediction models** — does not attempt machine learning statistical duration predictions.

---

## PostGIS & Geofencing Foundation (Phase 13)

```text
Incoming GPS Point (lat, lon)
       │
       ├──► Format as WGS-84 Point: POINT(longitude latitude) [SRID: 4326]
       │
       ├──► PostGIS ST_Distance / ST_DWithin (against BoardingPoint location)
       │
       └──► Reusable Geofence Service (app/services/geofence_service.py)
            - calculate_distance_meters(lat1, lon1, lat2, lon2)
            - is_within_geofence(lat1, lon1, lat2, lon2, radius_meters=100.0)
            - get_distance_to_boarding_point(lat, lon, boarding_point)
            - is_gps_within_boarding_point(lat, lon, boarding_point, radius_meters)
```

- **Spatial Representation:** Uses WGS 84 ellipsoid coordinate system (`SRID: 4326`). Coordinate order is strictly `POINT(longitude latitude)` (X=longitude, Y=latitude).
- **PostgreSQL / Docker:** Configured with `postgis/postgis:16-3.4-alpine` image in `docker-compose.yml`.
- **Configurable Radius:** Configured via `DEFAULT_GEOFENCE_RADIUS_METERS=100.0` in Pydantic settings.
- **GiST Spatial Indexing:** Created on `boarding_points` and `location_pings` spatial columns in target PostgreSQL + PostGIS environments.

---

## Parent–Child Linking & Approval Workflow (Phase 12)


```text
Parent Mobile App                          Student Web/App
       │                                          │
       ├──► 1. POST /api/v1/auth/register-parent   │
       │    (email, full_name, child_email)       │
       │                                          │
       ▼ (ParentLinkRequest: PENDING)             ▼
                                           2. GET /api/v1/parent-links
                                           3. POST /api/v1/parent-links/{id}/approve
                                                  │
                                                  ▼
                                           ParentChildren (APPROVED)
                                                  │
       ◄──────────────────────────────────────────┘
       │
       ├──► 4. GET /api/v1/parent/children (Lists approved children)
       │
       └──► 5. GET /api/v1/parent/children/{student_id}/live
            (Resolves child's assigned bus -> active trip -> Redis live telemetry)
```

- **Authorization Boundary:** Knowing a student's email, UUID, or trip ID gives **zero** access to location. Only an `APPROVED` row in `ParentChildren` unlocks tracking.
- **Student Privacy:** Only the referenced student can approve or reject a link request. Rejected or pending requests never reveal telemetry.
- **Trip Resolution:** Parents don't need driver IDs or trip IDs. The backend resolves `student.assigned_bus_id` to the currently `IN_PROGRESS` trip and fetches real-time Redis telemetry.

---

## Offline GPS Batch Synchronization (Phase 11)

```text
Driver Device (Offline)
       │ (Local Drift/SQLite Queue)
       ▼
Network Connectivity Restored
       │
       ▼ POST /api/v1/trips/{trip_id}/gps/sync (Batch: 1-500 points)
FastAPI Backend
       │
       ├──► Deduplication against PostgreSQL (LocationPing.client_id UUID)
       │    & Intra-Batch Deduplication
       │
       ├──► PostgreSQL: Bulk insert accepted points with server received_at
       │
       └──► Redis & WebSocket: Atomically advance live state only for newest recorded_at
```

- **Idempotency Guarantee:** Each queued point carries a client-generated UUID `client_id`. If mobile uploads retry due to transient connection dropouts, already inserted points are marked as `duplicates` without failing the batch.
- **Out-of-Order Handling:** PostgreSQL retains all accepted historical points chronologically, while Redis Lua script guarantees the live pointer moves monotonically forward.
- **Fault Tolerance:** Temporary Redis outages do not fail or roll back the primary PostgreSQL transaction.



---

## Running Automated Tests

```bash
pytest -v
```

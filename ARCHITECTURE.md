# Architecture Document

## System Overview
SMARTBUS is divided into three main components:
1. **Frontend (Mobile App):** Flutter (Dart)
2. **Backend (API):** FastAPI (Python)
3. **Database:** PostgreSQL

## 1. Frontend (Flutter)
- **State Management:** SetState / localized controllers.
- **Routing:** MaterialPageRoute for navigation.
- **Maps:** `flutter_map` with OpenStreetMap tiles.
- **Authentication:** Firebase Authentication (Email/Password & Google Sign-In) combined with custom backend JWTs/tokens.

## 2. Backend (FastAPI)
- **Framework:** FastAPI for high-performance async REST endpoints.
- **ORM:** SQLAlchemy (Async) mapped to PostgreSQL.
- **Authentication:** Validates Firebase ID tokens and sets Custom Claims (e.g., `role: PARENT`) to synchronize Firebase and DB roles.
- **Background Tasks:** APScheduler for trip status updates and offline detection.
- **Notifications:** Firebase Cloud Messaging (FCM) for push alerts.

## 3. Database (PostgreSQL)
### Core Tables:
- `users`: Stores all users with Enum roles (`STUDENT`, `PARENT`, `DRIVER`, `ADMIN`).
- `buses`, `routes`, `stops`: Transportation logistics.
- `driver_bus_assignments`, `student_bus_assignments`: Mapping users to buses.
- `tracking_sessions`, `location_pings`: Real-time GPS data.
- `emergencies`: SOS and accident logs.
- `parent_student_relationships`: Links parents to students (requires student approval).

## Data Flow
1. **GPS Pings:** Driver app sends location to FastAPI -> FastAPI stores in DB -> Triggers real-time ETA updates.
2. **Parent Request:** Parent requests access -> Student approves -> FastAPI updates DB -> Firebase Custom Claim `PARENT` is issued.

# SMARTBUS (YatraSetu)

SMARTBUS is a modern, real-time school bus tracking and management platform that connects Schools, Parents, and Drivers to ensure student safety and logistical efficiency.

## 🌟 Key Features
- **Role-Based Portals:** Dedicated, customized interfaces for Students, Parents, Drivers, and Administrators.
- **Real-Time GPS Tracking:** Live bus tracking using OpenStreetMap and real-time backend updates.
- **Automated Alerts & SOS:** Immediate push notifications for delays, route deviations, accidents, and driver-initiated SOS protocols.
- **Secure Parent Access:** Strict parent-student linking flow requiring active approval from students via their authenticated institutional accounts.

## 🏗️ Technology Stack
- **Frontend (Mobile App):** Flutter (Dart) with `flutter_map` for cartography.
- **Backend (API):** FastAPI (Python) for asynchronous, high-performance endpoints.
- **Database:** PostgreSQL managed via SQLAlchemy (Async).
- **Authentication:** Firebase Auth combined with JWT Custom Claims.
- **Background Tasks:** APScheduler for monitoring offline buses and trip lifecycle automation.

## 📚 Documentation
For detailed information about the project's architecture, design, and roadmap, please refer to the following documentation files:
- [Product Requirements (PRD.md)](PRD.md)
- [System Architecture (ARCHITECTURE.md)](ARCHITECTURE.md)
- [UI/UX Design (DESIGN.md)](DESIGN.md)
- [Development Rules (RULES.md)](RULES.md)
- [Task Tracker (TASKS.md)](TASKS.md)
- [Context & Decisions (MEMORY.md)](MEMORY.md)

## 🚀 Getting Started
### 1. Backend Setup
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
*(Requires a running PostgreSQL instance and `firebase-service-account.json` in the backend directory)*

### 2. Frontend Setup
```bash
cd frontend
flutter clean
flutter pub get
flutter run
```
*(Requires `google-services.json` / `GoogleService-Info.plist` for Firebase integration)*

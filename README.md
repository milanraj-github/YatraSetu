# SMARTBUS (YatraSetu) Ecosystem

SMARTBUS is a modern, real-time school bus tracking and management platform that connects Schools, Parents, and Drivers to ensure student safety and logistical efficiency. The ecosystem consists of a **Cross-Platform Mobile App** for end-users and a **Web Dashboard** for school administrators.

## 🌟 Key Features

### 📱 Mobile App (Students, Parents, Drivers)
- **Role-Based Portals:** Dedicated, customized interfaces for Students, Parents, and Drivers.
- **Real-Time GPS Tracking:** Live bus tracking on mobile using OpenStreetMap and real-time backend updates.
- **Automated Alerts & SOS:** Immediate push notifications for delays, route deviations, accidents, and driver-initiated SOS protocols.
- **Secure Parent Access:** Strict parent-student linking flow requiring active approval from students via their authenticated institutional accounts.

### 💻 Web Admin Dashboard (School Administrators)
- **Centralized Management:** Add, edit, and manage buses, routes, schedules, and drivers.
- **Live Fleet Tracking:** A bird's-eye view of all active school buses in real-time.
- **Emergency Escalation Hub:** A dedicated alert center to immediately monitor and respond to driver SOS signals or automated accident detections.
- **Analytics & Insights:** Monitor trip history, delays, and driver performance over time.

## 🏗️ Technology Stack
- **Frontend (Mobile App):** Flutter (Dart) with `flutter_map` for cartography.
- **Frontend (Web Admin):** React, Vite, Tailwind CSS, and TypeScript.
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

### 1. Backend Setup (FastAPI)
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
*(Requires a running PostgreSQL instance and `firebase-service-account.json` in the backend directory)*

### 2. Mobile App Setup (Flutter)
```bash
cd frontend
flutter clean
flutter pub get
flutter run
```
*(Requires `google-services.json` / `GoogleService-Info.plist` for Firebase integration)*

### 3. Admin Web Dashboard Setup (React/Vite)
```bash
cd smartbus_admin
npm install
npm run dev
```
*(Requires `.env` file configured with your backend API URL and Firebase Web credentials)*

.

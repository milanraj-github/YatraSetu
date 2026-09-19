# SMARTBUS — Campus Bus Tracking, Safety & Emergency Backend

> **Status:** Phase 1 only — project foundation.

SMARTBUS is a modern college campus transportation backend designed to support live bus tracking, passenger safety, parent-child approvals, and emergency handling across four roles: **Admin**, **Driver**, **Student**, and **Parent**.

---

## Phase 1 Overview

Phase 1 establishes a clean, production-oriented FastAPI foundation. No database, authentication, or business logic is implemented in this phase.

### Technologies Used (Phase 1)
- **Language:** Python 3.11+
- **Web Framework:** FastAPI
- **ASGI Server:** Uvicorn
- **Configuration & Validation:** Pydantic v2 & Pydantic Settings
- **Testing:** Pytest & HTTPX (FastAPI TestClient)

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
│   │   └── config.py        # Pydantic v2 settings & environment configuration
│   │
│   └── api/
│       ├── __init__.py
│       └── v1/
│           ├── __init__.py
│           └── health.py    # Health check router (/api/v1/health)
│
├── tests/
│   ├── __init__.py
│   └── test_health.py       # Pytest test suite
│
├── .env                     # Local environment variables (do not commit secrets)
├── .env.example             # Environment variables template
├── .gitignore               # Git ignore rules
├── requirements.txt         # Phase 1 project dependencies
└── README.md                # Project documentation
```

---

## Getting Started

### 1. Prerequisites
- Python 3.11 or higher installed.
- Git installed.

### 2. Create and Activate a Virtual Environment

**On Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt):**
```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
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

### 4. Environment Configuration

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
```

---

### 5. Running the Development Server

Start Uvicorn with live reload:

```bash
uvicorn app.main:app --reload
```

The application will start at `http://127.0.0.1:8000`.

---

## API Endpoints & Interactive Docs

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/` | `GET` | Root welcome message |
| `/api/v1/health` | `GET` | Service operational health check |
| `/docs` | `GET` | Interactive Swagger UI documentation |
| `/redoc` | `GET` | Interactive ReDoc documentation |
| `/openapi.json` | `GET` | OpenAPI 3.0 schema |

---

## Running Tests

Execute the automated test suite using Pytest:

```bash
pytest
```

To run with verbose output:

```bash
pytest -v
```

# SMARTBUS Backend — Phase 1 Authentication Module

Intelligent College Bus Tracking & Notification Platform  
**HPL 2026 • SMVITM Bantakal**

---

## 1. Authentication Architecture Overview

SMARTBUS uses a decoupled, production-oriented authentication & authorization architecture:

- **Firebase Authentication**: Handles primary identity verification, Email/Password sign-in, Google OAuth Sign-In, password resets, email verification, and issues standard short-lived Firebase ID Tokens (JWT).
- **FastAPI Backend**: Receives the Firebase ID Token in the `Authorization: Bearer <FIREBASE_ID_TOKEN>` header, verifies token authenticity via **Firebase Admin SDK**, enforces student email-domain restrictions (`@sode-edu.in`), and applies Role-Based Access Control (RBAC).
- **PostgreSQL Database**: Stores SMARTBUS user profile records (`users` table) mapped via `firebase_uid` and normalized `email`.

```text
Flutter App / Web
       |
       | Email/Password OR Google Sign-In
       v
Firebase Authentication (Issues Firebase ID Token)
       |
       | Header: Authorization Bearer <Token>
       v
FastAPI Backend (Verifies Token & Enforces @sode-edu.in Domain Guard)
       |
       v
PostgreSQL Database (Retrieves User Profile & Role)
       |
       +---> ADMIN (3 Predefined Provisioned Accounts)
       +---> DRIVER (3 Predefined Provisioned Accounts)
       +---> STUDENT (Dynamic Registrations; @sode-edu.in required)
```

---

## 2. Firebase Console Setup Guide

Follow these steps to configure Firebase Console for SMARTBUS:

1. **Create Firebase Project**:
   - Go to [Firebase Console](https://console.firebase.google.com/).
   - Click **Add project** and name it `SMARTBUS` (or `SMARTBUS-Dev`).

2. **Enable Authentication Providers**:
   - In the left sidebar, navigate to **Build** $\rightarrow$ **Authentication**.
   - Click **Get started**.
   - Under the **Sign-in method** tab:
     - Enable **Email/Password**.
     - Enable **Google** provider and configure support email.

3. **Configure Password Reset & Email Verification**:
   - In Authentication settings under **Templates**, customize the **Password reset** and **Email address verification** email templates.

4. **Generate Firebase Admin SDK Credentials**:
   - Navigate to **Project settings** (gear icon) $\rightarrow$ **Service accounts**.
   - Click **Generate new private key**.
   - Save the downloaded JSON file as `firebase-service-account.json` inside the `backend/` directory.
   - *Note: `firebase-service-account.json` is automatically listed in `.gitignore` to prevent committing secrets to source control.*

---

## 3. Environment & Local Setup

### 1. Create Virtual Environment & Install Dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

Edit `.env` to configure your PostgreSQL credentials and seed passwords:

```ini
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=your_password
POSTGRES_DB=smartbus_db

FIREBASE_SERVICE_ACCOUNT_PATH=firebase-service-account.json
STUDENT_REQUIRED_DOMAIN=sode-edu.in

# Predefined Admin Passwords
ADMIN1_EMAIL=admin1@sode-edu.in
ADMIN1_PASSWORD=Admin1_Password123!
ADMIN2_EMAIL=admin2@sode-edu.in
ADMIN2_PASSWORD=Admin2_Password123!
ADMIN3_EMAIL=admin3@sode-edu.in
ADMIN3_PASSWORD=Admin3_Password123!

# Predefined Driver Passwords
DRIVER1_EMAIL=driver1@sode-edu.in
DRIVER1_PASSWORD=Driver1_Password123!
DRIVER2_EMAIL=driver2@sode-edu.in
DRIVER2_PASSWORD=Driver2_Password123!
DRIVER3_EMAIL=driver3@sode-edu.in
DRIVER3_PASSWORD=Driver3_Password123!
```

---

## 4. Provisioning Predefined Admin & Driver Accounts

Admin and Driver accounts cannot be created dynamically by normal users. They are provisioned securely via an **idempotent seed script**.

Run the seed script:

```bash
python scripts/seed_auth_users.py
```

This script:
1. Checks if the account exists in **Firebase Auth**. If missing, creates the Firebase account with specified credentials and `email_verified=True`.
2. Checks if the account exists in **PostgreSQL**. If missing, inserts the user profile with `ADMIN` or `DRIVER` role.
3. Is **safe to run repeatedly** without creating duplicate entries.

### Predefined Account Credentials
- **Admins**:
  - `admin1@sode-edu.in`
  - `admin2@sode-edu.in`
  - `admin3@sode-edu.in`
- **Drivers**:
  - `driver1@sode-edu.in`
  - `driver2@sode-edu.in`
  - `driver3@sode-edu.in`

---

## 5. How User Registration & Auth Flows Work

### A. Student Email/Password Registration
1. Student registers on Flutter app using Firebase Auth.
2. Flutter obtains the Firebase ID token and calls `POST /api/v1/auth/sync-user` with `Authorization: Bearer <TOKEN>`.
3. FastAPI backend verifies the token and checks the email domain:
   - **Allowed**: `student@sode-edu.in` $\rightarrow$ Profile created in PostgreSQL with role `STUDENT`.
   - **Rejected**: `student@gmail.com` or `student@yahoo.com` $\rightarrow$ FastAPI returns `403 Forbidden` (`STUDENT_EMAIL_DOMAIN_NOT_ALLOWED`).

### B. Student Google Sign-In
1. Student signs in via Google OAuth on Flutter app.
2. Firebase Authentication issues a Firebase ID token.
3. Flutter calls `POST /api/v1/auth/sync-user`.
4. FastAPI checks the email domain of the Google account.
   - Google Account `sagar@sode-edu.in` $\rightarrow$ Accepted (`STUDENT` role).
   - Google Account `sagar@gmail.com` $\rightarrow$ Rejected (`403 Forbidden`).

### C. Forgot Password
- Triggered entirely via Firebase Client SDK (`firebase.auth().sendPasswordResetEmail(email)`).
- Users open the password reset link sent by Firebase to set a new password.
- No password reset tokens are stored in PostgreSQL.

### D. Email Verification
- Email verification state is synchronized from Firebase payload (`is_email_verified`).
- Unverified users can be filtered or enforced before granting sensitive API access.

---

## 6. Running the Backend Server

To start the FastAPI server with live reload:

```bash
uvicorn app.main:app --reload --port 8000
```

- Interactive API Docs (Swagger UI): [http://localhost:8000/docs](http://localhost:8000/docs)
- Alternative Docs (ReDoc): [http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 7. Running the Test Suite

The test suite includes 20+ automated tests running with in-memory SQLite and mock Firebase token verification.

Run all tests:

```bash
pytest
```

Run tests with verbose output:

```bash
pytest -v
```

---

## 8. API Endpoint Summary

| Method | Endpoint | Authorization | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/sync-user` | Bearer Firebase JWT | Syncs Firebase identity & creates student profile if `@sode-edu.in` |
| `GET` | `/api/v1/auth/me` | Bearer Firebase JWT | Returns current authenticated user profile |
| `POST` | `/api/v1/auth/logout` | Bearer Firebase JWT | Confirms client session logout |
| `GET` | `/api/v1/auth/admin-only` | Bearer JWT (Admin Role) | Verification endpoint for `ADMIN` role guard |
| `GET` | `/api/v1/auth/driver-only` | Bearer JWT (Driver Role) | Verification endpoint for `DRIVER` role guard |
| `GET` | `/api/v1/auth/student-only` | Bearer JWT (Student Role) | Verification endpoint for `STUDENT` role guard |

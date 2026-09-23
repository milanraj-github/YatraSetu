# Project Context & Decisions (MEMORY)

## Key Architectural Decisions
1. **No Backend Passwords:** We completely offloaded password management and email verification to Firebase Authentication. The backend only stores the `firebase_uid` and relies on Firebase ID tokens for authorization.
2. **Custom Claims for Roles:** Since anyone can sign up with an email, role authorization is strictly managed via Firebase Custom Claims (e.g., `role: PARENT`). The FastAPI backend sets these claims upon successful verification.
3. **Database Enums:** We use strict PostgreSQL Enums for status tracking (e.g., `ParentRequestStatus`, `RelationshipStatus`). 

## Important Lessons Learned & Gotchas
- **Token Caching:** Firebase caches ID tokens on the device. When the backend assigns a new role (like `PARENT`), the Flutter app MUST call `getIdToken(true)` to force a refresh, otherwise the user will get 403 Forbidden errors because their cached token still looks like a Student.
- **SQLAlchemy Enums:** When adding a new value to a Python `enum.Enum` that maps to a SQLAlchemy `Enum`, you must manually run an `ALTER TYPE name ADD VALUE 'NEW_VALUE'` command in PostgreSQL. The backend will crash with a 500 DataError if you try to insert an unmapped enum string.
- **Pydantic vs Dict:** Always remember that FastAPI dependencies return Pydantic objects. `current_user.email` works, `current_user["email"]` throws a TypeError.

## Environment Details
- **Student Domain:** Strictly restricted to `@sode-edu.in`.
- **Database:** PostgreSQL running locally / hosted instance.
- **Local Timezone:** `Asia/Kolkata` is heavily utilized by APScheduler for background jobs.

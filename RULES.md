# Development Rules & Guidelines

## 1. Backend Rules (Python/FastAPI)
- **Async First:** Always use `async def` for endpoints and `AsyncSession` for SQLAlchemy database operations.
- **Dependency Injection:** Use FastAPI `Depends()` for database sessions and authentication (`get_current_user`, `require_parent`, etc.).
- **Enums:** Database enums must exactly match Python Enums. If adding a new enum value (e.g., `COMPLETED`), update the PostgreSQL ENUM type manually using `ALTER TYPE` before modifying the Python code.
- **Pydantic Models:** Always use dot notation (`user.email`) for Pydantic objects returned by dependencies, NOT dictionary access (`user["email"]`).

## 2. Frontend Rules (Flutter)
- **Null Safety:** Strict null safety must be maintained. 
- **Token Refresh:** When updating user roles (e.g., granting Parent access), always force a Firebase token refresh (`user.getIdToken(true)`) and persist it so the backend receives the updated custom claims.
- **Error Handling:** Gracefully handle backend 500 errors. Avoid infinite loading spinners by explicitly setting `isLoading = false` in `catch` or `finally` blocks.
- **UI Consistency:** Use BottomNavigationBar for main role portals (Student, Parent, Driver) instead of top AppBar actions.

## 3. Git Rules
- Do not commit `.env`, `firebase-service-account.json`, `.dart_tool/`, or `venv/`.
- Ensure PRs are tested locally by running both the Uvicorn server and the Flutter app.

from typing import Optional, Dict
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from app.schemas.auth import UserResponse, SyncUserRequest, APIResponse, UserRole
from app.dependencies.auth import get_current_user, require_admin, require_driver, require_student
from app.core.database import get_db
from app.models.user import User, UserRole as DBUserRole, UserStatus

logger = logging.getLogger("smartbus.auth")
router = APIRouter(prefix="/auth", tags=["Authentication"])


async def _upsert_db_user(db: AsyncSession, current_user: UserResponse, full_name_override: Optional[str] = None) -> User:
    """
    Atomically insert-or-update the authenticated user in the PostgreSQL users table.
    Uses ON CONFLICT(email) DO UPDATE so re-authentication with new firebase_uid is handled.
    Role is always determined by the backend (never trusted from client).
    """
    full_name = full_name_override or current_user.full_name
    db_role = DBUserRole(current_user.role.value)

    # Upsert keyed on email (canonical identity). firebase_uid is updated if it changes.
    stmt = pg_insert(User).values(
        firebase_uid=current_user.firebase_uid,
        email=current_user.email,
        full_name=full_name,
        role=db_role,
        status=UserStatus.ACTIVE,
        is_email_verified=current_user.is_email_verified,
    ).on_conflict_do_update(
        index_elements=["email"],
        set_={
            "firebase_uid": current_user.firebase_uid,  # update if re-issued
            "full_name": full_name,
            "is_email_verified": current_user.is_email_verified,
            # role and status are not overwritten
        }
    )
    await db.execute(stmt)
    await db.commit()

    # Re-fetch to return the full ORM object
    result = await db.execute(select(User).where(User.email == current_user.email))
    db_user = result.scalars().first()
    logger.info(f"User synced to DB: {db_user.email} (role={db_user.role.value})")
    return db_user


@router.post("/sync-user", response_model=APIResponse[Dict[str, UserResponse]])
async def sync_user(
    request_data: Optional[SyncUserRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Synchronizes authenticated Firebase ID Token identity with SMARTBUS backend.
    - Upserts user into PostgreSQL users table on every login.
    - If user is a DRIVER, automatically evaluates & activates driver tracking session.
    """
    # Always upsert into DB
    full_name_override = request_data.full_name if request_data else None
    await _upsert_db_user(db, current_user, full_name_override=full_name_override)

    if current_user.role == UserRole.DRIVER:
        try:
            from app.api.v1.tracking import get_db_user_from_auth
            from app.services.tracking_service import get_driver_tracking_status
            db_driver = await get_db_user_from_auth(db, current_user)
            await get_driver_tracking_status(db, db_driver)
        except Exception as e:
            logger.warning(f"Driver session evaluation failed during sync: {e}")

    return APIResponse(
        success=True,
        data={"user": current_user}
    )

@router.get("/me", response_model=APIResponse[Dict[str, UserResponse]])
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    """
    Retrieves profile and role information for the currently authenticated user.
    """
    return APIResponse(
        success=True,
        data={"user": current_user}
    )

@router.post("/logout", response_model=APIResponse[Dict[str, str]])
async def logout(current_user: UserResponse = Depends(get_current_user)):
    """
    Client session logout confirmation.
    """
    return APIResponse(
        success=True,
        data={"message": "Logged out successfully."}
    )

# Role-Based Verification Test Endpoints
@router.get("/admin-only", response_model=APIResponse[Dict[str, str]])
async def admin_only_test(current_user: UserResponse = Depends(require_admin)):
    return APIResponse(
        success=True,
        data={"message": f"Welcome Admin {current_user.full_name}"}
    )

@router.get("/driver-only", response_model=APIResponse[Dict[str, str]])
async def driver_only_test(current_user: UserResponse = Depends(require_driver)):
    return APIResponse(
        success=True,
        data={"message": f"Welcome Driver {current_user.full_name}"}
    )

@router.get("/student-only", response_model=APIResponse[Dict[str, str]])
async def student_only_test(current_user: UserResponse = Depends(require_student)):
    return APIResponse(
        success=True,
        data={"message": f"Welcome Student {current_user.full_name}"}
    )

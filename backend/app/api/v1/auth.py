from typing import Optional, Dict
from fastapi import APIRouter, Depends
from app.schemas.auth import UserResponse, SyncUserRequest, APIResponse, UserRole
from app.dependencies.auth import get_current_user, require_admin, require_driver, require_student

router = APIRouter(prefix="/auth", tags=["Authentication"])

from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.v1.tracking import get_db_user_from_auth
from app.services.tracking_service import get_driver_tracking_status

@router.post("/sync-user", response_model=APIResponse[Dict[str, UserResponse]])
async def sync_user(
    request_data: Optional[SyncUserRequest] = None,
    db: AsyncSession = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Synchronizes authenticated Firebase ID Token identity with SMARTBUS backend.
    - If user is a DRIVER, automatically evaluates & activates driver tracking session.
    """
    if current_user.role == UserRole.DRIVER:
        try:
            db_driver = await get_db_user_from_auth(db, current_user)
            await get_driver_tracking_status(db, db_driver)
        except Exception:
            pass

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

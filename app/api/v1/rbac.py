from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.core.security import require_role, require_roles
from app.models.enums import UserRole
from app.models.user import User

router = APIRouter(prefix="/rbac", tags=["RBAC Verification"])


class RBACMessageResponse(BaseModel):
    """Response schema for RBAC verification endpoints."""

    message: str
    user_id: str
    role: str


@router.get(
    "/admin-test",
    response_model=RBACMessageResponse,
    summary="Admin RBAC Test",
    description="Endpoint restricted strictly to users with the ADMIN role.",
)
async def admin_test(
    current_user: User = Depends(require_role(UserRole.ADMIN)),
) -> RBACMessageResponse:
    """Admin-only test endpoint."""
    return RBACMessageResponse(
        message="Admin RBAC access granted",
        user_id=str(current_user.id),
        role=current_user.role.value,
    )


@router.get(
    "/driver-test",
    response_model=RBACMessageResponse,
    summary="Driver RBAC Test",
    description="Endpoint restricted strictly to users with the DRIVER role.",
)
async def driver_test(
    current_user: User = Depends(require_role(UserRole.DRIVER)),
) -> RBACMessageResponse:
    """Driver-only test endpoint."""
    return RBACMessageResponse(
        message="Driver RBAC access granted",
        user_id=str(current_user.id),
        role=current_user.role.value,
    )


@router.get(
    "/student-test",
    response_model=RBACMessageResponse,
    summary="Student RBAC Test",
    description="Endpoint restricted strictly to users with the STUDENT role.",
)
async def student_test(
    current_user: User = Depends(require_role(UserRole.STUDENT)),
) -> RBACMessageResponse:
    """Student-only test endpoint."""
    return RBACMessageResponse(
        message="Student RBAC access granted",
        user_id=str(current_user.id),
        role=current_user.role.value,
    )


@router.get(
    "/parent-test",
    response_model=RBACMessageResponse,
    summary="Parent RBAC Test",
    description="Endpoint restricted strictly to users with the PARENT role.",
)
async def parent_test(
    current_user: User = Depends(require_role(UserRole.PARENT)),
) -> RBACMessageResponse:
    """Parent-only test endpoint."""
    return RBACMessageResponse(
        message="Parent RBAC access granted",
        user_id=str(current_user.id),
        role=current_user.role.value,
    )


@router.get(
    "/admin-driver-test",
    response_model=RBACMessageResponse,
    summary="Admin or Driver RBAC Test",
    description="Endpoint accessible by users with either ADMIN or DRIVER roles.",
)
async def admin_driver_test(
    current_user: User = Depends(require_roles(UserRole.ADMIN, UserRole.DRIVER)),
) -> RBACMessageResponse:
    """Admin and Driver shared test endpoint."""
    return RBACMessageResponse(
        message="Admin/Driver RBAC access granted",
        user_id=str(current_user.id),
        role=current_user.role.value,
    )

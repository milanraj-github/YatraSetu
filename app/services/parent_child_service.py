import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Sequence
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.redis import get_redis_client
from app.models.enums import ParentLinkStatus, TripStatus, UserRole
from app.models.parent_child import ParentChildren, ParentLinkRequest
from app.models.trip import Trip
from app.models.user import User
from app.schemas.gps import LiveLocationResponse
from app.schemas.parent_child import (
    ParentChildResponse,
    ParentLinkRequestResponse,
    ParentRegisterRequest,
)
from app.services.gps_service import get_live_location_key

logger = logging.getLogger(__name__)


def build_parent_link_request_response(req: ParentLinkRequest) -> ParentLinkRequestResponse:
    """Helper to convert a ParentLinkRequest entity into its response schema."""
    return ParentLinkRequestResponse(
        id=req.id,
        parent_id=req.parent_id,
        student_id=req.student_id,
        status=req.status,
        approved_at=req.approved_at,
        created_at=req.created_at,
        updated_at=req.updated_at,
        parent_email=req.parent.email if req.parent else None,
        parent_name=req.parent.full_name if req.parent else None,
        student_email=req.student.email if req.student else None,
        student_name=req.student.full_name if req.student else None,
    )


async def register_parent_and_create_link_request(
    db: AsyncSession,
    firebase_identity: dict[str, Any],
    parent_in: ParentRegisterRequest,
) -> ParentLinkRequestResponse:
    """Register parent user profile and initiate a pending link request to a student."""
    firebase_uid = firebase_identity["uid"]
    child_email_clean = parent_in.child_email.strip().lower()
    parent_email_clean = parent_in.email.strip().lower()

    # 1. Look up student by email
    student_res = await db.execute(select(User).where(User.email == child_email_clean))
    student = student_res.scalar_one_or_none()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student with specified email not found",
        )

    # 2. Verify referenced user is a STUDENT
    if student.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Referenced user is not a student",
        )

    # 3. Look up or provision Parent User
    parent_res = await db.execute(select(User).where(User.firebase_uid == firebase_uid))
    parent_user = parent_res.scalar_one_or_none()

    if parent_user is None:
        # Check if email is already taken by a different user
        email_check = await db.execute(select(User).where(User.email == parent_email_clean))
        existing_by_email = email_check.scalar_one_or_none()
        if existing_by_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already registered with another account",
            )

        parent_user = User(
            firebase_uid=firebase_uid,
            email=parent_email_clean,
            full_name=parent_in.full_name,
            role=UserRole.PARENT,
        )
        db.add(parent_user)
        await db.flush()
    else:
        if parent_user.role != UserRole.PARENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Authenticated user does not have PARENT role",
            )

    if parent_user.id == student.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parent and student cannot be the same user",
        )

    # 4. Check for existing pending request or approved link
    existing_req_res = await db.execute(
        select(ParentLinkRequest)
        .options(selectinload(ParentLinkRequest.parent), selectinload(ParentLinkRequest.student))
        .where(
            ParentLinkRequest.parent_id == parent_user.id,
            ParentLinkRequest.student_id == student.id,
        )
        .order_by(ParentLinkRequest.created_at.desc())
    )
    existing_request = existing_req_res.scalars().first()

    if existing_request and existing_request.status == ParentLinkStatus.PENDING:
        return build_parent_link_request_response(existing_request)

    # 5. Create new link request in PENDING status
    new_request = ParentLinkRequest(
        parent_id=parent_user.id,
        student_id=student.id,
        status=ParentLinkStatus.PENDING,
    )
    db.add(new_request)
    await db.commit()

    # Re-fetch with relationships loaded
    loaded_res = await db.execute(
        select(ParentLinkRequest)
        .options(selectinload(ParentLinkRequest.parent), selectinload(ParentLinkRequest.student))
        .where(ParentLinkRequest.id == new_request.id)
    )
    loaded_request = loaded_res.scalar_one()
    return build_parent_link_request_response(loaded_request)


async def approve_parent_link_request(
    db: AsyncSession,
    request_id: uuid.UUID,
    current_student: User,
) -> ParentLinkRequestResponse:
    """Approve a pending parent-child linking request by the referenced student."""
    if current_student.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can approve link requests",
        )

    req_res = await db.execute(
        select(ParentLinkRequest)
        .options(selectinload(ParentLinkRequest.parent), selectinload(ParentLinkRequest.student))
        .where(ParentLinkRequest.id == request_id)
    )
    link_request = req_res.scalar_one_or_none()

    if not link_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent link request not found",
        )

    if link_request.student_id != current_student.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You cannot approve a request addressed to another student",
        )

    if link_request.status == ParentLinkStatus.REJECTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot approve a rejected link request",
        )

    if link_request.status == ParentLinkStatus.APPROVED:
        # Idempotent response
        return build_parent_link_request_response(link_request)

    # Transition to APPROVED
    link_request.status = ParentLinkStatus.APPROVED
    link_request.approved_at = datetime.now(timezone.utc)

    # Check if ParentChildren record exists
    pc_res = await db.execute(
        select(ParentChildren).where(
            ParentChildren.parent_id == link_request.parent_id,
            ParentChildren.student_id == link_request.student_id,
        )
    )
    if not pc_res.scalar_one_or_none():
        new_pc = ParentChildren(
            parent_id=link_request.parent_id,
            student_id=link_request.student_id,
        )
        db.add(new_pc)

    await db.commit()
    await db.refresh(link_request)
    return build_parent_link_request_response(link_request)


async def reject_parent_link_request(
    db: AsyncSession,
    request_id: uuid.UUID,
    current_student: User,
) -> ParentLinkRequestResponse:
    """Reject a pending parent-child linking request by the referenced student."""
    if current_student.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can reject link requests",
        )

    req_res = await db.execute(
        select(ParentLinkRequest)
        .options(selectinload(ParentLinkRequest.parent), selectinload(ParentLinkRequest.student))
        .where(ParentLinkRequest.id == request_id)
    )
    link_request = req_res.scalar_one_or_none()

    if not link_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent link request not found",
        )

    if link_request.student_id != current_student.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You cannot reject a request addressed to another student",
        )

    if link_request.status == ParentLinkStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reject an already approved link request",
        )

    if link_request.status == ParentLinkStatus.REJECTED:
        return build_parent_link_request_response(link_request)

    link_request.status = ParentLinkStatus.REJECTED
    await db.commit()
    await db.refresh(link_request)
    return build_parent_link_request_response(link_request)


async def get_student_parent_requests(
    db: AsyncSession,
    current_student: User,
) -> list[ParentLinkRequestResponse]:
    """Retrieve all parent link requests for the authenticated student."""
    if current_student.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can view their link requests",
        )

    res = await db.execute(
        select(ParentLinkRequest)
        .options(selectinload(ParentLinkRequest.parent), selectinload(ParentLinkRequest.student))
        .where(ParentLinkRequest.student_id == current_student.id)
        .order_by(ParentLinkRequest.created_at.desc())
    )
    requests = res.scalars().all()
    return [build_parent_link_request_response(r) for r in requests]


async def get_parent_children(
    db: AsyncSession,
    current_parent: User,
) -> list[ParentChildResponse]:
    """Retrieve all approved linked children for the authenticated parent."""
    if current_parent.role != UserRole.PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only parents can view linked children",
        )

    res = await db.execute(
        select(ParentChildren)
        .options(selectinload(ParentChildren.student))
        .where(ParentChildren.parent_id == current_parent.id)
        .order_by(ParentChildren.created_at.desc())
    )
    links = res.scalars().all()

    return [
        ParentChildResponse(
            id=link.id,
            student_id=link.student.id,
            student_name=link.student.full_name,
            student_email=link.student.email,
            assigned_bus_id=link.student.assigned_bus_id,
            created_at=link.created_at,
        )
        for link in links
    ]


async def get_child_live_location(
    db: AsyncSession,
    student_id: uuid.UUID,
    current_parent: User,
) -> LiveLocationResponse:
    """Retrieve current live location for an approved child's active bus trip."""
    if current_parent.role != UserRole.PARENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only parents can access child live location",
        )

    # 1. Verify approved parent-child link exists
    link_res = await db.execute(
        select(ParentChildren).where(
            ParentChildren.parent_id == current_parent.id,
            ParentChildren.student_id == student_id,
        )
    )
    if not link_res.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: You do not have an approved relationship with this student",
        )

    # 2. Retrieve student user record
    student_res = await db.execute(select(User).where(User.id == student_id))
    student = student_res.scalar_one_or_none()
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found",
        )

    if not student.assigned_bus_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student is not currently assigned to a bus",
        )

    # 3. Find active trip for the student's assigned bus
    trip_res = await db.execute(
        select(Trip).where(
            Trip.bus_id == student.assigned_bus_id,
            Trip.status == TripStatus.IN_PROGRESS,
        )
    )
    trip = trip_res.scalar_one_or_none()
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active in-progress trip found for the student's bus",
        )

    # 4. Fetch live location from Redis
    try:
        redis_client = get_redis_client()
        key = get_live_location_key(trip.id)
        raw_data = await redis_client.get(key)
    except Exception as exc:
        logger.error(f"Redis error getting child live location for trip {trip.id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Live location service temporarily unavailable",
        )

    if not raw_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No live location available for this trip",
        )

    data = json.loads(raw_data)
    return LiveLocationResponse(
        trip_id=uuid.UUID(data["trip_id"]),
        driver_id=uuid.UUID(data["driver_id"]),
        bus_id=uuid.UUID(data["bus_id"]),
        latitude=data["latitude"],
        longitude=data["longitude"],
        recorded_at=datetime.fromisoformat(data["recorded_at"]),
        received_at=datetime.fromisoformat(data["received_at"]),
        accuracy_meters=data.get("accuracy_meters"),
        speed_mps=data.get("speed_mps"),
        heading_degrees=data.get("heading_degrees"),
    )

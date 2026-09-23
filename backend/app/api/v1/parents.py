from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.schemas.auth import UserResponse, APIResponse, UserRole
from app.dependencies.auth import get_current_user, require_admin
from app.models.user import User, UserStatus
from app.models.parent_student_relationship import ParentStudentRelationship, RelationshipStatus
from app.schemas.parent import ParentDetailsResponse, ParentRelationshipWithStudentResponse

router = APIRouter(prefix="/admin/parents", tags=["Admin Parents"])

@router.get("", response_model=APIResponse)
async def get_all_parents(
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_admin)
):
    """Get all parents and their basic details"""
    stmt = (
        select(User)
        .where(User.role == UserRole.PARENT)
        .options(selectinload(User.student_relationships).selectinload(ParentStudentRelationship.student))
        .order_by(User.created_at.desc())
    )
    res = await db.execute(stmt)
    parents = res.scalars().all()
    
    parent_list = []
    for parent in parents:
        relationships = parent.student_relationships
        parent_list.append({
            "id": parent.id,
            "full_name": parent.full_name,
            "email": parent.email,
            "status": parent.status,
            "created_at": parent.created_at,
            "linked_students_count": len(relationships),
            "relationships": [
                {
                    "student_name": rel.student.full_name,
                    "student_email": rel.student.email,
                    "relationship_type": rel.relationship_type,
                    "status": rel.status
                }
                for rel in relationships
            ]
        })
        
    return APIResponse(success=True, data={"parents": parent_list})

@router.get("/{parent_id}", response_model=APIResponse)
async def get_parent_details(
    parent_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_admin)
):
    """Get details of a specific parent and their linked students"""
    stmt = (
        select(User)
        .where(User.id == parent_id, User.role == UserRole.PARENT)
        .options(selectinload(User.student_relationships).selectinload(ParentStudentRelationship.student))
    )
    res = await db.execute(stmt)
    parent = res.scalars().first()
    
    if not parent:
        raise HTTPException(status_code=404, detail="Parent not found")
        
    relationships = []
    for rel in parent.student_relationships:
        relationships.append({
            "id": rel.id,
            "parent_id": rel.parent_id,
            "student_id": rel.student_id,
            "relationship_type": rel.relationship_type,
            "status": rel.status,
            "requested_at": rel.requested_at,
            "approved_at": rel.approved_at,
            "rejected_at": rel.rejected_at,
            "revoked_at": rel.revoked_at,
            "created_at": rel.created_at,
            "updated_at": rel.updated_at,
            "student": {
                "id": rel.student.id,
                "full_name": rel.student.full_name,
                "email": rel.student.email,
                "status": rel.student.status
            }
        })
        
    parent_data = {
        "id": parent.id,
        "full_name": parent.full_name,
        "email": parent.email,
        "status": parent.status,
        "created_at": parent.created_at
    }
    
    return APIResponse(success=True, data={"parent": parent_data, "students": relationships})


@router.get("/relationships/all", response_model=APIResponse)
async def get_all_relationships(
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_admin)
):
    """Get all parent-student relationships"""
    stmt = (
        select(ParentStudentRelationship)
        .options(
            selectinload(ParentStudentRelationship.parent),
            selectinload(ParentStudentRelationship.student)
        )
        .order_by(ParentStudentRelationship.created_at.desc())
    )
    res = await db.execute(stmt)
    relationships = res.scalars().all()
    
    data = []
    for rel in relationships:
        data.append({
            "id": rel.id,
            "parent": {
                "id": rel.parent.id,
                "full_name": rel.parent.full_name,
                "email": rel.parent.email
            },
            "student": {
                "id": rel.student.id,
                "full_name": rel.student.full_name,
                "email": rel.student.email
            },
            "relationship_type": rel.relationship_type,
            "status": rel.status,
            "requested_at": rel.requested_at,
            "created_at": rel.created_at
        })
        
    return APIResponse(success=True, data={"relationships": data})

from app.models.parent_registration_request import ParentRegistrationRequest

@router.get("/requests/all", response_model=APIResponse)
async def get_all_parent_requests(
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(require_admin)
):
    """Admin views all parent registration requests"""
    stmt = select(ParentRegistrationRequest).order_by(ParentRegistrationRequest.created_at.desc())
    res = await db.execute(stmt)
    requests = res.scalars().all()
    
    data = []
    for r in requests:
        data.append({
            "id": r.id,
            "student_email": r.student_email,
            "relationship_type": r.relationship_type,
            "status": r.status,
            "created_at": r.created_at,
            "expires_at": r.expires_at,
            "used_at": r.used_at
        })
        
    return APIResponse(success=True, data={"requests": data})

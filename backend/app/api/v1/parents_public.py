from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone, timedelta
import secrets
import hashlib
import re

from app.core.database import get_db
from app.core.config import settings
from app.schemas.auth import APIResponse
from app.models.parent_registration_request import ParentRegistrationRequest, ParentRequestStatus
from app.models.parent_student_relationship import RelationshipType, ParentStudentRelationship, RelationshipStatus
from app.models.user import User, UserRole, UserStatus
from app.services.email_service import send_parent_request_email
from app.core.firebase import verify_firebase_id_token
from app.schemas.parent_registration import ParentRegistrationPayload
from firebase_admin import auth
from pydantic import BaseModel

class ParentRequestSchema(BaseModel):
    student_email: str
    relationship_type: RelationshipType

router = APIRouter(prefix="/parents", tags=["Public Parents"])

def generate_secure_token() -> (str, str):
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_hash

@router.post("/request", response_model=APIResponse)
async def request_parent_account(
    req: ParentRequestSchema,
    db: AsyncSession = Depends(get_db)
):
    email = req.student_email.strip().lower()
    if not re.match(r"^[\w\.-]+@[\w\.-]+\.\w+$", email):
        raise HTTPException(status_code=400, detail="Invalid email format.")
        
    if not email.endswith(f"@{settings.STUDENT_REQUIRED_DOMAIN}"):
        raise HTTPException(status_code=400, detail=f"Student email must end with @{settings.STUDENT_REQUIRED_DOMAIN}")
        
    stmt = select(ParentRegistrationRequest).where(
        ParentRegistrationRequest.student_email == email,
        ParentRegistrationRequest.relationship_type == req.relationship_type,
        ParentRegistrationRequest.status == ParentRequestStatus.PENDING
    )
    res = await db.execute(stmt)
    existing_request = res.scalars().first()
    
    if existing_request:
        now = datetime.now(timezone.utc)
        if existing_request.expires_at > now:
            return APIResponse(success=True, data={"message": "Parent request submitted. If the email is eligible, the student will receive a verification request."})

    token, token_hash = generate_secure_token()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.PARENT_REQUEST_TOKEN_EXPIRY_MINUTES)
    
    new_req = ParentRegistrationRequest(
        student_email=email,
        relationship_type=req.relationship_type,
        token_hash=token_hash,
        expires_at=expires_at,
        status=ParentRequestStatus.PENDING
    )
    db.add(new_req)
    await db.commit()
    
    email_sent = send_parent_request_email(email, req.relationship_type.value, token)
    if not email_sent:
        await db.delete(new_req)
        await db.commit()
        raise HTTPException(status_code=500, detail="Failed to send verification email. Please try again.")

    return APIResponse(success=True, data={"message": "Parent request submitted. If the email is eligible, the student will receive a verification request."})


@router.post("/register", response_model=APIResponse)
async def register_parent_account(
    req: ParentRegistrationPayload,
    db: AsyncSession = Depends(get_db)
):
    # 1. Verify token
    token_hash = hashlib.sha256(req.registration_token.encode()).hexdigest()
    stmt = select(ParentRegistrationRequest).where(
        ParentRegistrationRequest.token_hash == token_hash,
        ParentRegistrationRequest.status == ParentRequestStatus.APPROVED
    )
    res = await db.execute(stmt)
    parent_req = res.scalars().first()
    
    if not parent_req:
        raise HTTPException(status_code=400, detail="Invalid, expired, or unapproved registration token.")
        
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    r_expires = parent_req.expires_at.replace(tzinfo=None)
    
    if r_expires < now:
        parent_req.status = ParentRequestStatus.EXPIRED
        await db.commit()
        raise HTTPException(status_code=400, detail="Registration token has expired.")

    # 2. Verify Firebase Token
    decoded_token = verify_firebase_id_token(req.firebase_token)
    if not decoded_token:
        raise HTTPException(status_code=401, detail="Invalid Firebase token.")
        
    firebase_uid = decoded_token.get("uid")
    parent_email = decoded_token.get("email", "").lower().strip()
    
    if not firebase_uid or not parent_email:
        raise HTTPException(status_code=400, detail="Firebase token missing uid or email.")

    # 3. Handle PostgreSQL user creation
    user_stmt = select(User).where(User.email == parent_email)
    user_res = await db.execute(user_stmt)
    db_user = user_res.scalars().first()
    
    if db_user:
        if db_user.role != UserRole.PARENT:
            raise HTTPException(status_code=400, detail="This email is already registered with a different role.")
        db_user.firebase_uid = firebase_uid
        if req.full_name:
            db_user.full_name = req.full_name
    else:
        db_user = User(
            firebase_uid=firebase_uid,
            email=parent_email,
            full_name=req.full_name,
            role=UserRole.PARENT,
            status=UserStatus.ACTIVE,
            is_email_verified=bool(decoded_token.get("email_verified", False))
        )
        db.add(db_user)
        
    await db.flush()
    
    # 4. Resolve Student
    student_stmt = select(User).where(User.email == parent_req.student_email, User.role == UserRole.STUDENT)
    student_res = await db.execute(student_stmt)
    db_student = student_res.scalars().first()
    
    if not db_student:
        raise HTTPException(status_code=404, detail="The student associated with this request could not be found.")

    # 5. Create Relationship
    rel_stmt = select(ParentStudentRelationship).where(
        ParentStudentRelationship.parent_id == db_user.id,
        ParentStudentRelationship.student_id == db_student.id
    )
    rel_res = await db.execute(rel_stmt)
    existing_rel = rel_res.scalars().first()
    
    if existing_rel:
        if existing_rel.status != RelationshipStatus.ACTIVE:
            existing_rel.status = RelationshipStatus.ACTIVE
            existing_rel.relationship_type = parent_req.relationship_type
    else:
        new_rel = ParentStudentRelationship(
            parent_id=db_user.id,
            student_id=db_student.id,
            relationship_type=parent_req.relationship_type,
            status=RelationshipStatus.ACTIVE
        )
        db.add(new_rel)

    # 6. Mark Request Completed
    parent_req.status = ParentRequestStatus.COMPLETED
    parent_req.used_at = now
    
    # 7. Set Custom Claims (safely ignore if Firebase is mocked)
    try:
        if not settings.FIREBASE_MOCK_MODE:
            auth.set_custom_user_claims(firebase_uid, {"role": "PARENT"})
    except Exception as e:
        # Don't fail the whole transaction if custom claim fails, 
        # auth_service will still allow it if we add a hook or just rely on the DB sync.
        # Wait, if we rely on DB sync, auth_service.py #4 Dynamic Student Domain Validation rejects it!
        # So it IS critical. If it fails, raise exception to rollback DB!
        raise HTTPException(status_code=500, detail=f"Failed to set Firebase claims: {str(e)}")

    await db.commit()
    
    return APIResponse(success=True, data={"message": "Parent account registered successfully."})

@router.get("/request/verify", response_model=APIResponse)
async def verify_parent_request(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify a parent registration token.
    Returns the student email and status if valid.
    """
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    stmt = select(ParentRegistrationRequest).where(
        ParentRegistrationRequest.token_hash == token_hash
    )
    res = await db.execute(stmt)
    req = res.scalars().first()
    
    if not req:
        raise HTTPException(status_code=404, detail="Invalid registration token.")
        
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    r_expires = req.expires_at.replace(tzinfo=None)
    
    if r_expires < now and req.status not in (ParentRequestStatus.COMPLETED, ParentRequestStatus.REJECTED):
        req.status = ParentRequestStatus.EXPIRED
        await db.commit()
        raise HTTPException(status_code=400, detail="Registration token has expired.")
        
    return APIResponse(success=True, data={
        "student_email": req.student_email,
        "relationship_type": req.relationship_type.value,
        "status": req.status.value
    })

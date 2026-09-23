from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from app.models.parent_student_relationship import RelationshipType, RelationshipStatus
from app.schemas.auth import UserResponse

class ParentStudentRelationshipResponse(BaseModel):
    id: int
    parent_id: int
    student_id: int
    relationship_type: RelationshipType
    status: RelationshipStatus
    requested_at: datetime
    approved_at: Optional[datetime] = None
    rejected_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class ParentRelationshipWithStudentResponse(ParentStudentRelationshipResponse):
    student: UserResponse

class ParentDetailsResponse(BaseModel):
    parent: UserResponse
    students: List[ParentRelationshipWithStudentResponse] = []

    class Config:
        from_attributes = True
        
class CreateRelationshipRequest(BaseModel):
    parent_id: int
    student_id: int
    relationship_type: RelationshipType
    
class UpdateRelationshipStatusRequest(BaseModel):
    status: RelationshipStatus

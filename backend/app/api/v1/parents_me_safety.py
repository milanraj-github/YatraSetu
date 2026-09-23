from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import or_

from app.models.user import User, UserRole
from app.models.parent_student_relationship import ParentStudentRelationship, RelationshipStatus
from app.models.student_assignment import StudentBusAssignment, StudentAssignmentStatus
from app.models.emergency import Emergency, EmergencyStatus
from app.models.alert import Alert, AlertStatus

async def get_parent_safety_events(db: AsyncSession, db_parent: User):
    # 1. Fetch ACTIVE relationships and their students
    rel_stmt = (
        select(ParentStudentRelationship)
        .where(
            ParentStudentRelationship.parent_id == db_parent.id,
            ParentStudentRelationship.status == RelationshipStatus.ACTIVE
        )
        .options(selectinload(ParentStudentRelationship.student))
    )
    rel_res = await db.execute(rel_stmt)
    relationships = rel_res.scalars().all()
    
    if not relationships:
        return {"active_events": [], "recent_events": []}
        
    student_bus_map = {}
    bus_student_map = {}
    
    # 2. Get active bus assignments for these students
    for rel in relationships:
        student = rel.student
        asgn_stmt = select(StudentBusAssignment).where(
            StudentBusAssignment.student_id == student.id,
            StudentBusAssignment.status == StudentAssignmentStatus.ACTIVE
        ).options(selectinload(StudentBusAssignment.bus))
        asgn_res = await db.execute(asgn_stmt)
        asgn = asgn_res.scalars().first()
        
        if asgn and asgn.bus:
            student_bus_map[student.id] = asgn.bus
            if asgn.bus.id not in bus_student_map:
                bus_student_map[asgn.bus.id] = []
            bus_student_map[asgn.bus.id].append(student)
            
    if not bus_student_map:
        return {"active_events": [], "recent_events": []}
        
    bus_ids = list(bus_student_map.keys())
    
    active_events = []
    recent_events = []
    
    # 3. Fetch Emergencies
    em_stmt = select(Emergency).where(
        Emergency.bus_id.in_(bus_ids)
    ).order_by(Emergency.created_at.desc()).limit(20)
    em_res = await db.execute(em_stmt)
    emergencies = em_res.scalars().all()
    
    for em in emergencies:
        for student in bus_student_map[em.bus_id]:
            bus = student_bus_map[student.id]
            event = {
                "id": f"em_{em.id}",
                "event_category": "EMERGENCY",
                "event_type": em.type.value,
                "severity": em.severity.value,
                "status": em.status.value,
                "description": em.description or "Emergency Alert",
                "detected_at": em.created_at.isoformat(),
                "resolved_at": em.resolved_at.isoformat() if em.resolved_at else None,
                "latitude": em.latitude,
                "longitude": em.longitude,
                "student": {"id": student.id, "full_name": student.full_name},
                "bus": {"id": bus.id, "bus_number": bus.bus_number}
            }
            if em.status in [EmergencyStatus.RESOLVED]:
                recent_events.append(event)
            else:
                active_events.append(event)
                
    # 4. Fetch Alerts
    al_stmt = select(Alert).where(
        Alert.bus_id.in_(bus_ids)
    ).order_by(Alert.created_at.desc()).limit(20)
    al_res = await db.execute(al_stmt)
    alerts = al_res.scalars().all()
    
    for al in alerts:
        for student in bus_student_map[al.bus_id]:
            bus = student_bus_map[student.id]
            event = {
                "id": f"al_{al.id}",
                "event_category": "ALERT",
                "event_type": al.type.value,
                "severity": al.severity.value,
                "status": al.status.value,
                "description": al.description or "System Alert",
                "detected_at": al.created_at.isoformat(),
                "resolved_at": al.resolved_at.isoformat() if al.resolved_at else None,
                "latitude": None, # Alerts typically don't have lat/lng in this schema unless via trip
                "longitude": None,
                "student": {"id": student.id, "full_name": student.full_name},
                "bus": {"id": bus.id, "bus_number": bus.bus_number}
            }
            if al.status == AlertStatus.RESOLVED:
                recent_events.append(event)
            else:
                active_events.append(event)
                
    # Sort
    active_events.sort(key=lambda x: x["detected_at"], reverse=True)
    recent_events.sort(key=lambda x: x["detected_at"], reverse=True)
    
    return {
        "active_events": active_events,
        "recent_events": recent_events
    }

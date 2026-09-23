from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.models.emergency import EmergencyType, EmergencySeverity, EmergencyStatus

class EmergencyResponse(BaseModel):
    id: int
    type: EmergencyType
    severity: EmergencySeverity
    status: EmergencyStatus
    bus_id: Optional[int]
    driver_id: Optional[int]
    trip_id: Optional[int]
    route_id: Optional[int]
    latitude: Optional[float]
    longitude: Optional[float]
    accuracy: Optional[float]
    description: Optional[str]
    created_at: datetime
    updated_at: datetime
    acknowledged_at: Optional[datetime]
    acknowledged_by: Optional[int]
    resolved_at: Optional[datetime]
    resolved_by: Optional[int]

    model_config = ConfigDict(from_attributes=True)

class EmergencyUpdate(BaseModel):
    status: EmergencyStatus

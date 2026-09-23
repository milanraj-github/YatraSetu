from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime
from app.models.alert import AlertType, AlertSeverity, AlertStatus

class AlertResponse(BaseModel):
    id: int
    type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    bus_id: Optional[int]
    driver_id: Optional[int]
    route_id: Optional[int]
    trip_id: Optional[int]
    description: str
    source: str
    created_at: datetime
    updated_at: datetime
    resolved_at: Optional[datetime]
    resolved_by: Optional[int]

    model_config = ConfigDict(from_attributes=True)

class AlertUpdate(BaseModel):
    status: AlertStatus

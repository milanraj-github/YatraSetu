from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class DeviceTokenRegister(BaseModel):
    token: str
    platform: Optional[str] = None
    device_name: Optional[str] = None

class NotificationResponse(BaseModel):
    id: int
    event_type: str
    related_entity_id: Optional[int] = None
    title: str
    message: str
    priority: str
    status: str
    created_at: datetime
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

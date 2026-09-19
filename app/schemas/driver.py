import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict


class DriverAssignmentResponse(BaseModel):
    """Response schema for driver bus assignment details."""

    driver_id: uuid.UUID
    driver_name: str
    driver_email: str
    assigned_bus_id: Optional[uuid.UUID] = None
    assigned_bus_number: Optional[str] = None
    assigned_bus_registration: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

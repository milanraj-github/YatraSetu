from pydantic import BaseModel

class ParentRegistrationPayload(BaseModel):
    firebase_token: str
    registration_token: str
    full_name: str

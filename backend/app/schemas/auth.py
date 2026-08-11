import uuid

from pydantic import BaseModel, EmailStr

from app.models.user import UserRole


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class CurrentUser(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: UserRole
    store_id: uuid.UUID | None = None
    linked_employee_id: uuid.UUID | None = None

    class Config:
        from_attributes = True

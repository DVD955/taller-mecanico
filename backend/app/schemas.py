from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from .models import UserRole, UserStatus


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    full_name: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole


class RegisterResponse(BaseModel):
    user: "UserResponse"
    recovery_code: str


class ResetPasswordRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    recovery_code: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: UserRole
    status: UserStatus
    active_session: bool

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    user: UserResponse

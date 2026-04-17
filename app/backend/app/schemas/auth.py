from typing import List, Optional
import uuid

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    company_name: str = Field(..., min_length=2, max_length=255)
    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: "UserResponse"
    tenant: "TenantResponse"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    tenant_id: str
    email: str
    name: str
    role: str
    is_active: bool
    last_active_at: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class TenantResponse(BaseModel):
    id: str
    company_name: str
    domain: Optional[str] = None
    plan: str
    commodities: list = []
    target_markets: list = []
    certifications: list = []
    about: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class TenantUpdateRequest(BaseModel):
    company_name: Optional[str] = None
    domain: Optional[str] = None
    commodities: Optional[List[str]] = None
    target_markets: Optional[List[str]] = None
    certifications: Optional[List[str]] = None
    about: Optional[str] = None


class InviteMemberRequest(BaseModel):
    email: EmailStr
    name: str = Field(..., min_length=2, max_length=255)
    role: str = "member"


class UpdateMemberRoleRequest(BaseModel):
    role: str


class MemberResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_active: bool
    last_active_at: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class MeResponse(BaseModel):
    user: UserResponse
    tenant: TenantResponse


TokenResponse.model_rebuild()

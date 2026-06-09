from typing import Optional

from pydantic import BaseModel


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenPayload(BaseModel):
    sub: str
    exp: int
    type: str
    role: Optional[str] = None

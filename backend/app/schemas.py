from pydantic import BaseModel
from typing import Optional


# =========================================================
# DOCUMENT SCHEMAS
# =========================================================

class DocumentCreate(BaseModel):
    title: str
    content: str = ""


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None


# =========================================================
# AUTHENTICATION SCHEMAS
# =========================================================

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
import re

EMAIL_REGEX = re.compile(r"^[\w\.\+\-]+@[\w\-]+\.[a-zA-Z]{2,}$")

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = Field(default=None, alias="fullName")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = v.strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email format")
        return clean

class UserLogin(BaseModel):
    email: str
    password: str

    model_config = ConfigDict(populate_by_name=True)

class UserOut(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import UserRole
from app.schemas.family import validate_palestine_id


class UserBase(BaseModel):
    username: str
    email: EmailStr
    full_name: str | None = None
    role: UserRole
    block_id: int | None = None
    shelter_id: int | None = None


class UserCreate(UserBase):
    password: str


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    role: UserRole | None = None
    block_id: int | None = None
    shelter_id: int | None = None
    password: str | None = None


class UserResponse(UserBase):
    id: int
    is_active: bool
    # Read-back allows any stored value (e.g. a seeded admin email that
    # wouldn't pass current EmailStr rules) without breaking listing.
    email: str = Field(default="", max_length=255)

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: str | None = None
    role: UserRole | None = None


class FamilyLoginSchema(BaseModel):
    national_id: int
    date_of_birth: date

    @field_validator("national_id")
    @classmethod
    def validate_national_id(cls, v):
        return validate_palestine_id(v)

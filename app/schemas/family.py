from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, field_validator, ConfigDict

from app.models.enums import Gender, HousingType, MaritalStatus, ResidencyStatus


# --- Helper: Luhn Algorithm Validator ---
def validate_palestine_id(value: int) -> int:
    """
    Validates that the ID is exactly 9 digits and satisfies the Luhn algorithm.
    Used for both Member and Family schemas.
    """
    # Convert to string to check length
    s_id = str(value)

    # 1. Check Length
    if len(s_id) != 9:
        raise ValueError("ID number must be exactly 9 digits long.")

    # 2. Luhn Checksum
    # Pad with leading zeros if necessary (though length check above enforces 9)
    # s_id = s_id.zfill(9)

    total = 0
    for i, digit_char in enumerate(s_id):
        digit = int(digit_char)
        # Multiply digit by 1 for even index, 2 for odd index (1-based logic)
        # Actually in 0-based index: even index -> weight 1, odd index -> weight 2
        # Standard ID logic:
        step = digit * ((i % 2) + 1)

        if step > 9:
            step -= 9
        total += step

    if total % 10 != 0:
        raise ValueError("Invalid ID number (Checksum failure).")

    return value


# -------------------------------------
# Member Schemas
# -------------------------------------


class MemberBase(BaseModel):
    id: int
    full_name: str
    gender: Gender
    marital_status: MaritalStatus
    date_of_birth: date
    relationship_to_head_id: int = 1

    # Health & Status
    has_chronic_disease: bool = False
    injured: bool = False
    disabled: bool = False
    pregnant: bool = False
    breastfeeding: bool = False

    # --- Validators ---

    @field_validator("id")
    @classmethod
    def validate_member_id(cls, v):
        return validate_palestine_id(v)

    @field_validator("pregnant", "breastfeeding", mode="after")
    @classmethod
    def validate_pregnancy_and_breastfeeding(cls, v, info):
        # We need to check the 'gender' field which is a sibling field.
        # Note: In Pydantic v2, we access values differently, but this logic
        # assumes standard validation flow.
        if v is True:
            # We access the already validated values or the raw input
            values = info.data
            if (
                values.get("gender") == Gender.MALE
                or values.get("marital_status") == MaritalStatus.SINGLE.value
            ):
                raise ValueError(
                    "Male & Single members cannot be marked as pregnant or breastfeeding"
                )
        return v


class MemberCreate(MemberBase):
    pass


class MemberResponse(MemberBase):
    family_id: int

    model_config = ConfigDict(from_attributes=True)


class MemberUpdate(BaseModel):
    name: Optional[str] = None
    # We usually don't update IDs or Date of Birth as they are constants,
    # but we can allow fixing typos if needed.
    marital_status: Optional[MaritalStatus] = None

    # Health Status Updates (The most common changes)
    has_chronic_disease: Optional[bool] = None
    injured: Optional[bool] = None
    disabled: Optional[bool] = None
    pregnant: Optional[bool] = None
    breastfeeding: Optional[bool] = None

    @field_validator("pregnant", "breastfeeding", mode="after")
    @classmethod
    def validate_pregnancy_and_breastfeeding_update(cls, v, info):
        # Validation logic similar to create, but we might not have gender here.
        # We will handle the gender check in the API logic for updates.
        if v is True:
            # We access the already validated values or the raw input
            values = info.data
            if values.get("marital_status") == MaritalStatus.SINGLE.value:
                raise ValueError("Single members cannot be marked as pregnant")
        return v


# -------------------------------------
# Family Schemas
# -------------------------------------


class FamilyBase(BaseModel):
    head_id: int
    spouse_id: Optional[int]

    female_headed: bool = False
    child_headed: bool = False

    primary_phone_number: str
    secondary_phone_number: str | None = None

    residency_status: ResidencyStatus
    housing_type: HousingType

    original_governor_id: int
    original_city_id: int
    current_governor_id: int
    current_city_id: int
    current_shelter_center_id: int
    shelter_block_id: int
    shelter_quality_id: Optional[int] = None
    # --- Validators ---

    @field_validator("head_id", "spouse_id")
    @classmethod
    def validate_member_id(cls, v):
        return validate_palestine_id(v)


class FamilyCreate(FamilyBase):
    members: List[MemberCreate]

    # TODO: load the head and spouse ids from members data insted
    @field_validator("members")
    @classmethod
    def validate_head_exists(cls, members, info):
        """
        Validate that the head_id listed in the family details
        actually exists in the provided members list.
        """
        values = info.data
        head_id = values.get("head_id")

        # Get all IDs from the proposed member list
        member_ids = [m.id for m in members]

        if head_id not in member_ids:
            raise ValueError(
                f"The Head of Family ID ({head_id}) must be included in the members list."
            )
        return members


class FamilyResponse(FamilyBase):
    id: int

    is_active: bool
    created_at: datetime
    archived_at: Optional[datetime] = None

    members: List[MemberResponse]

    model_config = ConfigDict(from_attributes=True)


class FamilyUpdate(BaseModel):
    # Only allow updating fields that change over time
    primary_phone_number: Optional[str] = None
    secondary_phone_number: Optional[str] = None
    residency_status: Optional[ResidencyStatus] = None
    housing_type: Optional[HousingType] = None
    female_headed: Optional[bool] = None
    child_headed: Optional[bool] = None
    original_governor_id: Optional[int] = None
    original_city_id: Optional[int] = None
    current_governor_id: Optional[int] = None
    current_city_id: Optional[int] = None
    current_shelter_center_id: Optional[int] = None
    shelter_block_id: Optional[int] = None
    shelter_quality_id: Optional[int] = None
    members: Optional[List[MemberUpdate]] = None

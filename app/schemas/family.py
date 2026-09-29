from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.models.enums import (
    Gender,
    HousingType,
    MaritalStatus,
    ResidencyStatus,
    UpdateRequestStatus,
    UpdateRequestType,
)


# --- Helper: Luhn Algorithm Validator ---
def validate_palestine_id(value: int) -> int:
    """
    Validates that the ID is exactly 9 digits and satisfies the Luhn algorithm.
    Used for both Member and Family schemas.
    """
    # Convert to string to check length
    s_id = str(value)

    # 1. Check Length
    if len(s_id) != 9 or s_id[0] not in "4789":
        raise ValueError(
            "ID number must be exactly 9 digits long and start with one of "
            "these numbers '4789'."
        )

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

    @model_validator(mode="after")
    def check_pregnancy_logic(self):
        if (self.pregnant or self.breastfeeding) and (
            self.gender == Gender.MALE or self.marital_status == MaritalStatus.SINGLE
        ):
            raise ValueError("Invalid pregnancy/breastfeeding status")
        return self


class MemberCreate(MemberBase):
    pass


class MemberResponse(MemberBase):
    family_id: int
    family_head_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class MemberUpdate(BaseModel):
    full_name: str | None = None
    # We usually don't update IDs or Date of Birth as they are constants,
    # but we can allow fixing typos if needed.
    marital_status: MaritalStatus | None = None

    # Health Status Updates (The most common changes)
    has_chronic_disease: bool | None = None
    injured: bool | None = None
    disabled: bool | None = None
    pregnant: bool | None = None
    breastfeeding: bool | None = None


# -------------------------------------
# Family Schemas
# -------------------------------------


class FamilyBase(BaseModel):
    head_id: int
    spouse_id: int | None = None

    female_headed: bool = False
    child_headed: bool = False

    primary_phone_number: str
    secondary_phone_number: str | None = None

    residency_status: ResidencyStatus
    housing_type: HousingType

    original_city_id: int
    current_shelter_center_id: int
    shelter_block_id: int | None
    shelter_quality_id: int | None = None
    # --- Validators ---

    @field_validator("head_id", "spouse_id")
    @classmethod
    def validate_member_id(cls, v):
        if v:
            return validate_palestine_id(v)
        else:
            return v


class FamilyCreate(FamilyBase):
    members: list[MemberCreate]

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
                f"The Head of Family ID ({head_id}) must be included "
                "in the members list."
            )
        return members


class FamilyResponse(FamilyBase):
    id: int

    is_active: bool
    created_at: datetime
    archived_at: datetime | None = None
    head: MemberResponse
    spouse: MemberResponse | None = None
    members: list[MemberResponse]

    model_config = ConfigDict(from_attributes=True)


class FamilyListResponse(FamilyBase):
    """Lists families. Excludes members to avoid heavy payloads and lazy-load issues."""

    id: int
    is_active: bool
    created_at: datetime
    archived_at: datetime | None = None
    head_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class FamilyUpdate(BaseModel):
    # Only allow updating fields that change over time.
    # Current governor/city is derived from current_shelter_center_id;
    # original governorate is derived from original_city_id.
    primary_phone_number: str | None = None
    secondary_phone_number: str | None = None
    residency_status: ResidencyStatus | None = None
    housing_type: HousingType | None = None
    female_headed: bool | None = None
    child_headed: bool | None = None
    original_city_id: int | None = None
    current_shelter_center_id: int | None = None
    shelter_block_id: int | None = None
    shelter_quality_id: int | None = None
    members: list[MemberUpdate] | None = None


class UpdateRequestCreate(BaseModel):
    request_type: UpdateRequestType
    payload: dict


class UpdateRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    family_id: int
    request_type: UpdateRequestType
    payload: dict
    status: UpdateRequestStatus
    reviewed_by_id: int | None = None
    reviewed_at: datetime | None = None
    created_at: datetime | None = None

from dataclasses import dataclass
from datetime import date
from typing import Literal

from fastapi import Query

from app.models.enums import (
    Gender,
    HousingType,
    MaritalStatus,
    ResidencyStatus,
)


@dataclass
class FamilyFilterParams:
    is_active: bool | None = Query(default=None)
    residency_status: ResidencyStatus | None = Query(default=None)
    female_headed: bool | None = Query(default=None)
    child_headed: bool | None = Query(default=None)

    # --- MULTI-SELECT FILTERS ---
    housing_type: list[HousingType] | None = Query(default=None)
    current_shelter_center_id: list[int] | None = Query(default=None)
    shelter_block_id: list[int] | None = Query(default=None)
    current_city_id: list[int] | None = Query(default=None)
    original_city_id: list[int] | None = Query(default=None)
    shelter_quality_id: list[int] | None = Query(default=None)
    current_governor_id: list[int] | None = Query(default=None)
    original_governor_id: list[int] | None = Query(default=None)

    head_name: str | None = Query(default=None)
    phone_number: str | None = Query(default=None)

    sort_by: Literal["id", "created_at", "is_active"] | None = Query(default="id")
    sort_order: Literal["asc", "desc"] | None = Query(default="desc")


@dataclass
class MemberFilterParams:
    family_id: int | None = Query(default=None)
    gender: Gender | None = Query(default=None)

    # National ID lookup: exact or prefix match (staff commonly have a
    # partial ID from a paper form)
    national_id: str | None = Query(default=None)

    # --- MULTI-SELECT FILTERS ---
    marital_status: list[MaritalStatus] | None = Query(default=None)
    relationship_to_head_id: list[int] | None = Query(default=None)

    current_shelter_center_id: list[int] | None = Query(default=None)
    shelter_block_id: list[int] | None = Query(default=None)

    has_chronic_disease: bool | None = Query(default=None)
    injured: bool | None = Query(default=None)
    disabled: bool | None = Query(default=None)
    pregnant: bool | None = Query(default=None)
    breastfeeding: bool | None = Query(default=None)

    dob_from: date | None = Query(default=None)
    dob_to: date | None = Query(default=None)

    full_name: str | None = Query(default=None)

    sort_by: Literal["id", "full_name", "date_of_birth"] | None = Query(default="id")
    sort_order: Literal["asc", "desc"] | None = Query(default="asc")

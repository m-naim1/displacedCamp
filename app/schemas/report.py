from datetime import date, datetime

from pydantic import BaseModel


class FamilyReportRow(BaseModel):
    family_id: int
    serial_no: str | None = None
    head_name: str | None = None
    head_id_number: int | None = None
    head_gender: str | None = None
    head_marital_status: str | None = None
    spouse_name: str | None = None
    spouse_id_number: int | None = None
    phone_1: str | None = None
    phone_2: str | None = None
    original_governorate: str | None = None
    original_city: str | None = None
    current_city: str | None = None
    site: str | None = None
    site_code: str | None = None
    camp_name: str | None = None
    block: str | None = None
    block_code: str | None = None
    shelter_type: str | None = None
    residency_status: str | None = None
    women_headed: bool = False
    child_headed: bool = False
    is_active: bool = False

    # Aggregated Counts
    member_count: int = 0
    male_count: int = 0
    female_count: int = 0
    daughters_count: int = 0
    sons_count: int = 0
    females_18_plus_count: int = 0
    under_2_count: int = 0
    under_2_male_count: int = 0
    under_2_female_count: int = 0
    under_3_count: int = 0
    under_5_count: int = 0
    under_18_count: int = 0
    adult_count: int = 0
    age_3_5_count: int = 0
    age_3_5_male_count: int = 0
    age_3_5_female_count: int = 0
    age_6_18_count: int = 0
    age_6_18_male_count: int = 0
    age_6_18_female_count: int = 0
    age_19_60_count: int = 0
    age_19_60_male_count: int = 0
    age_19_60_female_count: int = 0
    elderly_60_plus_count: int = 0
    elderly_60_plus_male_count: int = 0
    elderly_60_plus_female_count: int = 0
    disabled_any: bool = False
    disabled_count: int = 0
    injured_count: int = 0
    chronic_any: bool = False
    chronic_count: int = 0
    pregnant_count: int = 0
    breastfeeding_count: int = 0
    pregnant_or_breastfeeding_count: int = 0
    pregnant_or_breastfeeding_any: bool = False
    unaccompanied_children_count: int = 0
    accompanied_child_count: int = 0

    created_at: datetime | None = None
    updated_at: datetime | None = None


class MemberReportRow(BaseModel):
    serial_no: str | None = None
    member_id: int
    member_name: str | None = None
    member_id_number: int | None = None
    family_id: int | None = None
    family_head_name: str | None = None
    family_phone_1: str | None = None
    age: int | None = None
    dob: date | None = None
    gender: str | None = None
    relation: str | None = None
    marital_status: str | None = None
    site: str | None = None
    block: str | None = None
    disabled: bool = False
    injured: bool = False
    chronic_disease: bool = False
    pregnant: bool = False
    breastfeeding: bool = False
    accompanied_child: bool = False
    family_is_active: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None

"""Bulk family import from CSV.

One row per member; rows sharing the same `family_code` form one family.
The row flagged `is_head=true` (exactly one per family) supplies the head,
and that row also carries the family-level fields (phone, shelter, etc.).
This mirrors how registration sheets are collected in the field — families
are listed together, members one per line.

Required columns: family_code, member_id, full_name, gender, marital_status,
date_of_birth, relationship_to_head_id, is_head, primary_phone_number,
residency_status, housing_type, original_city_id, current_shelter_center_id.
Optional: shelter_block_id, shelter_quality_id, secondary_phone_number,
female_headed, child_headed, and the five health flags.
"""

import csv
import io
from dataclasses import dataclass, field

from pydantic import ValidationError as PydanticValidationError

from app.schemas.family import FamilyCreate, MemberCreate

REQUIRED_COLUMNS = [
    "family_code",
    "member_id",
    "full_name",
    "gender",
    "marital_status",
    "date_of_birth",
    "relationship_to_head_id",
    "is_head",
    "primary_phone_number",
    "residency_status",
    "housing_type",
    "original_city_id",
    "current_shelter_center_id",
]

_TRUTHY = {"true", "1", "yes", "y"}


def _to_bool(value: str | None) -> bool:
    return (value or "").strip().lower() in _TRUTHY


def _to_int(value: str | None) -> int | None:
    value = (value or "").strip()
    return int(value) if value.isdigit() else None


@dataclass
class ImportRowError:
    row: int
    family_code: str
    message: str


@dataclass
class ImportResult:
    families: list[FamilyCreate] = field(default_factory=list)
    errors: list[ImportRowError] = field(default_factory=list)


def parse_families_csv(content: str) -> ImportResult:
    """Parse CSV text into validated FamilyCreate payloads, collecting
    per-row/per-family errors instead of failing the whole file."""
    result = ImportResult()
    reader = csv.DictReader(io.StringIO(content))

    header = reader.fieldnames or []
    missing = [c for c in REQUIRED_COLUMNS if c not in header]
    if missing:
        result.errors.append(
            ImportRowError(row=1, family_code="", message=f"Missing columns: {missing}")
        )
        return result

    grouped: dict[str, dict] = {}
    for i, row in enumerate(reader, start=2):  # row 1 is the header
        code = (row.get("family_code") or "").strip()
        if not code:
            result.errors.append(
                ImportRowError(row=i, family_code="", message="Missing family_code")
            )
            continue

        entry = grouped.setdefault(
            code, {"row": i, "members": [], "head_id": None, "family_fields": None, "errors": []}
        )

        try:
            member = MemberCreate(
                id=_to_int(row.get("member_id")),
                full_name=(row.get("full_name") or "").strip(),
                gender=(row.get("gender") or "").strip(),
                marital_status=(row.get("marital_status") or "").strip(),
                date_of_birth=(row.get("date_of_birth") or "").strip(),
                relationship_to_head_id=_to_int(row.get("relationship_to_head_id")) or 1,
                has_chronic_disease=_to_bool(row.get("has_chronic_disease")),
                injured=_to_bool(row.get("injured")),
                disabled=_to_bool(row.get("disabled")),
                pregnant=_to_bool(row.get("pregnant")),
                breastfeeding=_to_bool(row.get("breastfeeding")),
            )
        except PydanticValidationError as e:
            entry["errors"].append(e.errors()[0]["msg"])
            continue

        entry["members"].append(member)
        if _to_bool(row.get("is_head")):
            if entry["head_id"]:
                entry["errors"].append("More than one is_head=true row")
            entry["head_id"] = member.id
            entry["family_fields"] = row  # family-level fields ride on the head's row

    for code, entry in grouped.items():
        if entry["errors"]:
            result.errors.append(
                ImportRowError(
                    row=entry["row"], family_code=code, message="; ".join(entry["errors"])
                )
            )
            continue
        if not entry["head_id"]:
            result.errors.append(
                ImportRowError(
                    row=entry["row"],
                    family_code=code,
                    message="No row with is_head=true for this family",
                )
            )
            continue

        raw = entry["family_fields"]
        try:
            result.families.append(
                FamilyCreate(
                    head_id=entry["head_id"],
                    spouse_id=None,
                    female_headed=_to_bool(raw.get("female_headed")),
                    child_headed=_to_bool(raw.get("child_headed")),
                    primary_phone_number=(raw.get("primary_phone_number") or "").strip(),
                    secondary_phone_number=(raw.get("secondary_phone_number") or "").strip()
                    or None,
                    residency_status=(raw.get("residency_status") or "").strip(),
                    housing_type=(raw.get("housing_type") or "").strip(),
                    original_city_id=_to_int(raw.get("original_city_id")) or 0,
                    current_shelter_center_id=_to_int(raw.get("current_shelter_center_id")) or 0,
                    shelter_block_id=_to_int(raw.get("shelter_block_id")),
                    shelter_quality_id=_to_int(raw.get("shelter_quality_id")),
                    members=entry["members"],
                )
            )
        except PydanticValidationError as e:
            result.errors.append(
                ImportRowError(
                    row=entry["row"],
                    family_code=code,
                    message="; ".join(err["msg"] for err in e.errors()[:3]),
                )
            )

    return result

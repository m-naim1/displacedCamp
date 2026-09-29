from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base
from app.models.enums import (
    Gender,
    HousingType,
    MaritalStatus,
    ResidencyStatus,
    UpdateRequestStatus,
    UpdateRequestType,
)
from app.models.lookups import (
    City,
    RelationshipToHead,
    ShelterBlock,
    ShelterCenter,
    ShelterQuality,
)


# --- Models ---
class Family(Base):
    __tablename__ = "families"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )

    head_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("members.id"), unique=True, index=True, nullable=True
    )
    spouse_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("members.id"), unique=False, nullable=True, index=True
    )

    residency_status: Mapped[ResidencyStatus] = mapped_column(
        Enum(ResidencyStatus, native_enum=False)
    )
    female_headed: Mapped[bool] = mapped_column(Boolean, default=False)
    child_headed: Mapped[bool] = mapped_column(Boolean, default=False)
    primary_phone_number: Mapped[str] = mapped_column(String, nullable=False)
    secondary_phone_number: Mapped[str] = mapped_column(String, nullable=True)

    original_city_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cities.id"), nullable=False
    )

    current_shelter_center_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("shelter_centers.id"), nullable=False
    )
    shelter_block_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("shelter_block.id"), nullable=True
    )
    # shelter_type_id: Mapped[int] = mapped_column(
    #     Integer, ForeignKey("shelter_types.id"), nullable=False
    # )
    housing_type: Mapped[HousingType] = mapped_column(
        Enum(HousingType, native_enum=False)
    )
    shelter_quality_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("shelter_quality.id"), nullable=True
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, index=True
    )  # Default is True (Active)
    created_at: Mapped[date] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    archived_at: Mapped[date | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # Date they left

    # --- Relationships ---
    members: Mapped[list[Member]] = relationship(
        "Member",
        back_populates="family",
        foreign_keys="[Member.family_id]",
        cascade="all, delete-orphan",
    )
    head: Mapped[Member] = relationship(
        "Member", foreign_keys=[head_id], back_populates="head_family"
    )
    spouse: Mapped[Member] = relationship(
        "Member", foreign_keys=[spouse_id], back_populates="spouse_family"
    )

    original_city: Mapped[City] = relationship(foreign_keys=[original_city_id])

    current_shelter_center: Mapped[ShelterCenter] = relationship(
        foreign_keys=[current_shelter_center_id]
    )
    shelter_block: Mapped[ShelterBlock] = relationship(foreign_keys=[shelter_block_id])
    shelter_quality: Mapped[ShelterQuality] = relationship(
        foreign_keys=[shelter_quality_id]
    )

    @property
    def head_name(self) -> str | None:
        return self.head.full_name if self.head else None


class Member(Base):
    __tablename__ = "members"
    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=False
    )
    family_id: Mapped[int] = mapped_column(Integer, ForeignKey("families.id"))
    full_name: Mapped[str] = mapped_column(String)
    gender: Mapped[Gender] = mapped_column(Enum(Gender, native_enum=False))
    marital_status: Mapped[MaritalStatus] = mapped_column(
        Enum(MaritalStatus, native_enum=False), default=MaritalStatus.SINGLE
    )
    date_of_birth: Mapped[date] = mapped_column(Date)
    relationship_to_head_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("relationships_to_head.id"), nullable=False
    )
    # --- Health Status ---
    has_chronic_disease: Mapped[bool] = mapped_column(Boolean, default=False)
    injured: Mapped[bool] = mapped_column(Boolean, default=False)
    disabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Pregnancy & Breastfeeding Status
    # Note: Status is only True if gender == FEMALE & marital_status != SINGLE
    pregnant: Mapped[bool] = mapped_column(Boolean, default=False)
    breastfeeding: Mapped[bool] = mapped_column(Boolean, default=False)

    # --- Relationships ---
    family: Mapped[Family] = relationship(
        "Family", back_populates="members", foreign_keys=[family_id]
    )
    relationship_to_head: Mapped[RelationshipToHead] = relationship(
        foreign_keys=[relationship_to_head_id]
    )

    head_family: Mapped[Family] = relationship(
        "Family", foreign_keys=[Family.head_id], back_populates="head", viewonly=True
    )
    spouse_family: Mapped[Family] = relationship(
        "Family",
        foreign_keys=[Family.spouse_id],
        back_populates="spouse",
        viewonly=True,
    )

    @property
    def family_head_name(self) -> str | None:
        return self.family.head.full_name if self.family and self.family.head else None


class FamilyUpdateRequest(Base):
    __tablename__ = "family_update_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    family_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("families.id"), nullable=False
    )
    request_type: Mapped[UpdateRequestType] = mapped_column(
        Enum(UpdateRequestType, native_enum=False)
    )
    payload: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False
    )  # Stores the proposed JSON changes
    status: Mapped[UpdateRequestStatus] = mapped_column(
        Enum(UpdateRequestStatus, native_enum=False),
        default=UpdateRequestStatus.PENDING,
    )

    reviewed_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    family: Mapped[Family] = relationship("Family", foreign_keys=[family_id])

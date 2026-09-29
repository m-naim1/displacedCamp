from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base

if TYPE_CHECKING:
    pass


class LookupBase(Base):
    __abstract__ = True

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name_en: Mapped[str] = mapped_column(String(128), nullable=False)
    name_ar: Mapped[str] = mapped_column(String(128), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class RelationshipToHead(LookupBase):
    __tablename__ = "relationships_to_head"


class ShelterQuality(LookupBase):
    __tablename__ = "shelter_quality"


class Governor(LookupBase):
    __tablename__ = "governors"
    cities: Mapped[list[City]] = relationship(back_populates="governor")


class City(LookupBase):
    __tablename__ = "cities"
    governor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("governors.id"), nullable=False
    )
    governor: Mapped[Governor] = relationship(back_populates="cities")
    shelter_centers: Mapped[list[ShelterCenter]] = relationship(back_populates="city")


class ShelterCenter(LookupBase):
    __tablename__ = "shelter_centers"
    city_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("cities.id"), nullable=False
    )
    city: Mapped[City] = relationship(back_populates="shelter_centers")
    shelter_blocks: Mapped[list[ShelterBlock]] = relationship(
        back_populates="shelter_center"
    )


class ShelterBlock(LookupBase):
    __tablename__ = "shelter_block"
    shelter_center_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("shelter_centers.id"), nullable=False
    )
    shelter_center: Mapped[ShelterCenter] = relationship(
        back_populates="shelter_blocks"
    )

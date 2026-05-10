from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, Boolean, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship, Mapped, mapped_column, validates
from sqlalchemy.sql import func
from app.db.session import Base
from app.models.enums import UserRole
from app.models.lookups import ShelterBlock


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(
        String, unique=True, index=True, nullable=False
    )
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False), default=UserRole.MANAGER, nullable=False
    )
    # Scope Fields
    # Which block does this user manage? (Only for blockHead)
    block_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("shelter_block.id"), nullable=True, index=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    block: Mapped[Optional["ShelterBlock"]] = relationship(
        "ShelterBlock", foreign_keys=[block_id], uselist=False
    )

    @validates("role")
    def validate_scope(self, key, role):
        if role == UserRole.BLOCK_HEAD and self.block_id is None:
            raise ValueError("BLOCK_HEAD users must have a block_id assigned")
        if role in (UserRole.SUPERADMIN, UserRole.MANAGER):
            if self.block_id is not None:
                raise ValueError(
                    "SUPERADMIN and MANAGER users should not have a scope assigned"
                )
        return role


class BlockHeadPermission(Base):
    __tablename__ = "block_head_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True
    )
    can_edit: Mapped[bool] = mapped_column(default=False)
    can_add: Mapped[bool] = mapped_column(default=False)
    can_delete: Mapped[bool] = mapped_column(default=False)

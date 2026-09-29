from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, event
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.db.session import Base
from app.models.enums import UserRole
from app.models.lookups import ShelterBlock, ShelterCenter


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
    block_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("shelter_block.id"), nullable=True, index=True
    )
    # which camp this user mange? (only for manager)
    shelter_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("shelter_centers.id"), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # Relationships
    block: Mapped[ShelterBlock | None] = relationship(
        "ShelterBlock", foreign_keys=[block_id], uselist=False, lazy="joined"
    )
    shelter: Mapped[ShelterCenter | None] = relationship(
        "ShelterCenter", foreign_keys=[shelter_id], uselist=False
    )

    def _validate_scope(self):
        """Enforces role/scope consistency.
        Runs at flush time (before_insert / before_update) so it is independent
        of the order in which attributes are assigned during construction.
        """
        if self.role == UserRole.BLOCK_HEAD and self.block_id is None:
            raise ValueError("BLOCK_HEAD users must have a block assigned")
        if self.role in (UserRole.SUPERADMIN, UserRole.MANAGER):
            if self.block_id is not None:
                raise ValueError(
                    "SUPERADMIN and MANAGER users should not have a block assigned"
                )
        if self.role == UserRole.MANAGER and self.shelter_id is None:
            raise ValueError("MANAGER users must have a shelter assigned")
        if self.role in (UserRole.SUPERADMIN, UserRole.BLOCK_HEAD):
            if self.shelter_id is not None:
                raise ValueError(
                    "SUPERADMIN and BLOCK_HEAD users should not have a shelter assigned"
                )


@event.listens_for(User, "before_insert")
@event.listens_for(User, "before_update")
def _validate_user_scope(mapper, connection, target):
    target._validate_scope()

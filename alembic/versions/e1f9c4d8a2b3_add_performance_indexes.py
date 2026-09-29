"""add performance indexes

Revision ID: e1f9c4d8a2b3
Revises: b3e8f7a2c1d4
Create Date: 2026-09-16 12:00:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1f9c4d8a2b3"
down_revision: str | Sequence[str] | None = "b3e8f7a2c1d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add indexes on the FK/aggregation columns that drive the slowest queries.

    - families.current_shelter_center_id / shelter_block_id / original_city_id:
      used on virtually every scoped filter (manager/block-head + reports).
    - members.family_id: inner driver of the report aggregation subqueries and
      the member list joins.
    - members.date_of_birth: dashboard age-band counts.
    """
    op.create_index(
        "ix_families_current_shelter_center_id",
        "families",
        ["current_shelter_center_id"],
        unique=False,
    )
    op.create_index(
        "ix_families_shelter_block_id",
        "families",
        ["shelter_block_id"],
        unique=False,
    )
    op.create_index(
        "ix_families_original_city_id",
        "families",
        ["original_city_id"],
        unique=False,
    )
    op.create_index(
        "ix_members_family_id",
        "members",
        ["family_id"],
        unique=False,
    )
    op.create_index(
        "ix_members_date_of_birth",
        "members",
        ["date_of_birth"],
        unique=False,
    )
    op.create_index(
        "ix_family_update_requests_reviewed_by_id",
        "family_update_requests",
        ["reviewed_by_id"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the added indexes."""
    op.drop_index("ix_family_update_requests_reviewed_by_id", table_name="family_update_requests")
    op.drop_index("ix_members_date_of_birth", table_name="members")
    op.drop_index("ix_members_family_id", table_name="members")
    op.drop_index("ix_families_original_city_id", table_name="families")
    op.drop_index("ix_families_shelter_block_id", table_name="families")
    op.drop_index("ix_families_current_shelter_center_id", table_name="families")
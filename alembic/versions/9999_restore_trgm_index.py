"""restore trgm index

Revision ID: 9999_restore_trgm
Revises: e1f9c4d8a2b3  # <-- Make sure this matches your latest migration
Create Date: 2026-10-08 12:00:00.000000
"""
from typing import Sequence, Union
from alembic import op

revision: str = '9999_restore_trgm'
down_revision: Union[str, Sequence[str], None] = 'e1f9c4d8a2b3' # UPDATE THIS
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.create_index(
        "ix_members_full_name_trgm",
        "members",
        ["full_name"],
        postgresql_using="gin",
        postgresql_ops={"full_name": "gin_trgm_ops"},
    )

def downgrade() -> None:
    op.drop_index("ix_members_full_name_trgm", table_name="members")

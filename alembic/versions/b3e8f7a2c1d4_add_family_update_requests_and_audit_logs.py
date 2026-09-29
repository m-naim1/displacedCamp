"""add family_update_requests and audit_logs tables

Revision ID: b3e8f7a2c1d4
Revises: 828d7e30f902
Create Date: 2026-09-09 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b3e8f7a2c1d4'
down_revision: Union[str, Sequence[str], None] = '828d7e30f902'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _json_type():
    return sa.JSON().with_variant(postgresql.JSONB(), 'postgresql')


def upgrade() -> None:
    """Create the family self-service update-request table and the audit trail."""
    op.create_table(
        'family_update_requests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('family_id', sa.Integer(), nullable=False),
        sa.Column('request_type', sa.String(), nullable=False),
        sa.Column('payload', _json_type(), nullable=False),
        sa.Column('status', sa.String(), nullable=False),
        sa.Column('reviewed_by_id', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['family_id'], ['families.id'], name=op.f('fk_family_update_requests_family_id_families')),
        sa.ForeignKeyConstraint(['reviewed_by_id'], ['users.id'], name=op.f('fk_family_update_requests_reviewed_by_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_family_update_requests')),
    )
    op.create_index(op.f('ix_family_update_requests_family_id'), 'family_update_requests', ['family_id'], unique=False)
    op.create_index(op.f('ix_family_update_requests_status'), 'family_update_requests', ['status'], unique=False)

    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('actor_username', sa.String(), nullable=False),
        sa.Column('actor_role', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('entity_id', sa.String(), nullable=True),
        sa.Column('details', _json_type(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_audit_logs_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_logs')),
    )
    op.create_index(op.f('ix_audit_logs_user_id'), 'audit_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_action'), 'audit_logs', ['action'], unique=False)
    op.create_index(op.f('ix_audit_logs_entity_type'), 'audit_logs', ['entity_type'], unique=False)
    op.create_index(op.f('ix_audit_logs_entity_id'), 'audit_logs', ['entity_id'], unique=False)
    op.create_index(op.f('ix_audit_logs_created_at'), 'audit_logs', ['created_at'], unique=False)


def downgrade() -> None:
    """Drop the audit trail and update-request tables."""
    op.drop_index(op.f('ix_audit_logs_created_at'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_entity_id'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_entity_type'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_action'), table_name='audit_logs')
    op.drop_index(op.f('ix_audit_logs_user_id'), table_name='audit_logs')
    op.drop_table('audit_logs')

    op.drop_index(op.f('ix_family_update_requests_status'), table_name='family_update_requests')
    op.drop_index(op.f('ix_family_update_requests_family_id'), table_name='family_update_requests')
    op.drop_table('family_update_requests')

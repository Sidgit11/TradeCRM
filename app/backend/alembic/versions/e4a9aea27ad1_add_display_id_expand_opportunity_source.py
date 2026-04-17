"""add_display_id_expand_opportunity_source

Revision ID: e4a9aea27ad1
Revises: 0f85e49321ff
Create Date: 2026-04-14 15:42:08.103991

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'e4a9aea27ad1'
down_revision: Union[str, None] = '0f85e49321ff'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add display_id column
    op.add_column('pipeline_opportunities', sa.Column('display_id', sa.String(length=20), nullable=True))
    op.create_index(op.f('ix_pipeline_opportunities_display_id'), 'pipeline_opportunities', ['display_id'], unique=True)

    # Expand opportunity_source enum with new values
    op.execute("ALTER TYPE opportunity_source ADD VALUE IF NOT EXISTS 'inbound_email'")
    op.execute("ALTER TYPE opportunity_source ADD VALUE IF NOT EXISTS 'referral'")
    op.execute("ALTER TYPE opportunity_source ADD VALUE IF NOT EXISTS 'whatsapp'")
    op.execute("ALTER TYPE opportunity_source ADD VALUE IF NOT EXISTS 'trade_show'")


def downgrade() -> None:
    op.drop_index(op.f('ix_pipeline_opportunities_display_id'), table_name='pipeline_opportunities')
    op.drop_column('pipeline_opportunities', 'display_id')
    # Note: PostgreSQL does not support removing enum values

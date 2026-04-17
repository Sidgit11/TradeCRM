"""add_message_templates

Revision ID: 5d865cd221d5
Revises: e4a9aea27ad1
Create Date: 2026-04-15 14:53:43.559363

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '5d865cd221d5'
down_revision: Union[str, None] = 'e4a9aea27ad1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('message_templates',
    sa.Column('tenant_id', sa.UUID(), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('channel', sa.Enum('email', 'whatsapp', name='template_channel'), nullable=False),
    sa.Column('category', sa.Enum('introduction', 'price_update', 'follow_up', 'sample_offer', 'order_confirmation', 'festive_greeting', 'reactivation', 'custom', name='template_category'), nullable=False),
    sa.Column('subject', sa.String(length=500), nullable=True),
    sa.Column('body', sa.Text(), nullable=False),
    sa.Column('body_format', sa.String(length=10), server_default='plain', nullable=False),
    sa.Column('variables', postgresql.JSON(astext_type=sa.Text()), server_default='[]', nullable=True),
    sa.Column('description', sa.String(length=500), nullable=True),
    sa.Column('is_archived', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('is_default', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('ai_generated', sa.Boolean(), server_default='false', nullable=False),
    sa.Column('ai_prompt', sa.Text(), nullable=True),
    sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('usage_count', sa.Integer(), server_default='0', nullable=False),
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_message_templates_tenant_category', 'message_templates', ['tenant_id', 'category'], unique=False)
    op.create_index('ix_message_templates_tenant_channel', 'message_templates', ['tenant_id', 'channel'], unique=False)
    op.create_index(op.f('ix_message_templates_tenant_id'), 'message_templates', ['tenant_id'], unique=False)

    op.add_column('campaign_steps', sa.Column('message_template_id', sa.UUID(), nullable=True))
    op.create_foreign_key('fk_campaign_steps_template', 'campaign_steps', 'message_templates', ['message_template_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    op.drop_constraint('fk_campaign_steps_template', 'campaign_steps', type_='foreignkey')
    op.drop_column('campaign_steps', 'message_template_id')
    op.drop_index(op.f('ix_message_templates_tenant_id'), table_name='message_templates')
    op.drop_index('ix_message_templates_tenant_channel', table_name='message_templates')
    op.drop_index('ix_message_templates_tenant_category', table_name='message_templates')
    op.drop_table('message_templates')

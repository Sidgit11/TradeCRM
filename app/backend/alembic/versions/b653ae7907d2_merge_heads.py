"""merge_heads

Revision ID: b653ae7907d2
Revises: 332cc0a096b1, 4d2176092dbf
Create Date: 2026-04-01 13:33:41.905087

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b653ae7907d2'
down_revision: Union[str, None] = ('332cc0a096b1', '4d2176092dbf')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

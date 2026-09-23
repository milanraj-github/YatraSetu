"""Add COMPLETED to parentrequeststatus

Revision ID: 68d64f40c066
Revises: 1bf5d248ab89
Create Date: 2026-09-22 20:21:03.073657

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '68d64f40c066'
down_revision: Union[str, Sequence[str], None] = '1bf5d248ab89'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

"""add operating_mode to decisions

Revision ID: f8e02fc1a614
Revises: 4323ba37038e
Create Date: 2026-08-29 17:13:39.061804

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f8e02fc1a614'
down_revision: Union[str, None] = '4323ba37038e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    operating_mode_enum = postgresql.ENUM(
        'NORMAL_MODE', 'ECO_MODE', 'EMERGENCY_MODE', name='operating_mode'
    )
    operating_mode_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'decisions',
        sa.Column(
            'operating_mode',
            postgresql.ENUM('NORMAL_MODE', 'ECO_MODE', 'EMERGENCY_MODE', name='operating_mode', create_type=False),
            nullable=False,
        ),
    )
    op.add_column('decisions', sa.Column('operating_mode_reason', sa.String(length=2000), nullable=False))


def downgrade() -> None:
    op.drop_column('decisions', 'operating_mode_reason')
    op.drop_column('decisions', 'operating_mode')
    postgresql.ENUM(name='operating_mode').drop(op.get_bind(), checkfirst=True)

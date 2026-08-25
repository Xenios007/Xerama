"""add media qc attempts

Revision ID: a1b2c3d4e5f6
Revises: 516daeedc39b
Create Date: 2026-08-25 06:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '516daeedc39b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('media_qc_attempts',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('asset_id', sa.String(length=32), nullable=False),
    sa.Column('dimension', sa.String(length=32), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('score', sa.Float(), nullable=False, server_default='0.0'),
    sa.Column('evidence', sa.JSON(), nullable=False),
    sa.Column('reasons', sa.JSON(), nullable=False),
    sa.Column('repair_recommendation', sa.Text(), nullable=False, server_default=''),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_media_qc_attempts_asset_id'), 'media_qc_attempts', ['asset_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_media_qc_attempts_asset_id'), table_name='media_qc_attempts')
    op.drop_table('media_qc_attempts')

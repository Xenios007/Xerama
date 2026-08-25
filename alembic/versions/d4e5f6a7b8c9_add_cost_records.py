"""add cost records

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-08-25 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('cost_records',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('provider', sa.String(length=64), nullable=False),
    sa.Column('model', sa.String(length=128), nullable=False),
    sa.Column('stage', sa.String(length=64), nullable=False),
    sa.Column('project_id', sa.String(length=32), nullable=True),
    sa.Column('series_id', sa.String(length=32), nullable=True),
    sa.Column('episode_id', sa.String(length=32), nullable=True),
    sa.Column('scene_number', sa.Integer(), nullable=True),
    sa.Column('shot_number', sa.Integer(), nullable=True),
    sa.Column('attempt', sa.Integer(), nullable=False, server_default='1'),
    sa.Column('quantity', sa.Float(), nullable=False, server_default='0.0'),
    sa.Column('unit', sa.String(length=16), nullable=False, server_default=''),
    sa.Column('cost_usd', sa.Float(), nullable=True),
    sa.Column('cost_known', sa.Boolean(), nullable=False, server_default=sa.false()),
    sa.Column('latency_ms', sa.Float(), nullable=True),
    sa.Column('asset_id', sa.String(length=32), nullable=True),
    sa.Column('failure_reason', sa.Text(), nullable=False, server_default=''),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_cost_records_project_id'), 'cost_records', ['project_id'], unique=False)
    op.create_index(op.f('ix_cost_records_episode_id'), 'cost_records', ['episode_id'], unique=False)
    op.create_index(op.f('ix_cost_records_stage'), 'cost_records', ['stage'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_cost_records_stage'), table_name='cost_records')
    op.drop_index(op.f('ix_cost_records_episode_id'), table_name='cost_records')
    op.drop_index(op.f('ix_cost_records_project_id'), table_name='cost_records')
    op.drop_table('cost_records')

"""add episode renders

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-08-25 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('episode_renders',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('episode_id', sa.String(length=32), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('render_asset_id', sa.String(length=32), nullable=False),
    sa.Column('parent_render_id', sa.String(length=32), nullable=True),
    sa.Column('source_script_version', sa.Integer(), nullable=False),
    sa.Column('input_asset_ids', sa.JSON(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['episode_id'], ['episodes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_episode_renders_episode_id'), 'episode_renders', ['episode_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_episode_renders_episode_id'), table_name='episode_renders')
    op.drop_table('episode_renders')

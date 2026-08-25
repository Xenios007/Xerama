"""add episode metrics and human feedback

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-08-25 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('episode_metrics',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('episode_id', sa.String(length=32), nullable=False),
    sa.Column('render_version', sa.Integer(), nullable=False),
    sa.Column('source', sa.String(length=64), nullable=False),
    sa.Column('observation_window_start', sa.DateTime(), nullable=False),
    sa.Column('observation_window_end', sa.DateTime(), nullable=False),
    sa.Column('impressions', sa.Integer(), nullable=True),
    sa.Column('views', sa.Integer(), nullable=True),
    sa.Column('avg_watch_seconds', sa.Float(), nullable=True),
    sa.Column('completion_rate', sa.Float(), nullable=True),
    sa.Column('three_second_retention_rate', sa.Float(), nullable=True),
    sa.Column('rewatch_rate', sa.Float(), nullable=True),
    sa.Column('continuation_rate', sa.Float(), nullable=True),
    sa.Column('engagement', sa.JSON(), nullable=False),
    sa.Column('raw_payload', sa.JSON(), nullable=False),
    sa.Column('imported_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['episode_id'], ['episodes.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_episode_metrics_episode_id'), 'episode_metrics', ['episode_id'], unique=False)
    op.create_index(op.f('ix_episode_metrics_source'), 'episode_metrics', ['source'], unique=False)

    op.create_table('human_feedback',
    sa.Column('id', sa.String(length=32), nullable=False),
    sa.Column('asset_id', sa.String(length=32), nullable=False),
    sa.Column('project_id', sa.String(length=32), nullable=True),
    sa.Column('decision', sa.String(length=32), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False, server_default=''),
    sa.Column('rating', sa.Integer(), nullable=True),
    sa.Column('tags', sa.JSON(), nullable=False),
    sa.Column('reviewer', sa.String(length=128), nullable=False, server_default=''),
    sa.Column('provider', sa.String(length=64), nullable=False, server_default=''),
    sa.Column('model', sa.String(length=128), nullable=False, server_default=''),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_human_feedback_asset_id'), 'human_feedback', ['asset_id'], unique=False)
    op.create_index(op.f('ix_human_feedback_project_id'), 'human_feedback', ['project_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_human_feedback_project_id'), table_name='human_feedback')
    op.drop_index(op.f('ix_human_feedback_asset_id'), table_name='human_feedback')
    op.drop_table('human_feedback')
    op.drop_index(op.f('ix_episode_metrics_source'), table_name='episode_metrics')
    op.drop_index(op.f('ix_episode_metrics_episode_id'), table_name='episode_metrics')
    op.drop_table('episode_metrics')

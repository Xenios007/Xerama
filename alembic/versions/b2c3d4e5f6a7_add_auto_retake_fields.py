"""add auto retake fields

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-25 07:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # MODULE-045 - explicit server_default so this stays forward-compatible
    # against a non-empty table, same precedent as MODULE-041's job-queue
    # migration.
    for table in ("storyboards", "shot_video_productions", "shot_audio_productions"):
        op.add_column(
            table, sa.Column("auto_retake_attempts", sa.Integer(), nullable=False, server_default="0")
        )
        op.add_column(
            table, sa.Column("escalated", sa.Boolean(), nullable=False, server_default=sa.false())
        )


def downgrade() -> None:
    """Downgrade schema."""
    for table in ("storyboards", "shot_video_productions", "shot_audio_productions"):
        op.drop_column(table, "escalated")
        op.drop_column(table, "auto_retake_attempts")

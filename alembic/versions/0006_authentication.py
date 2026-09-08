"""add authenticated user claim fields

Revision ID: 0006_authentication
Revises: 0005_alcohol
Create Date: 2026-09-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0006_authentication"
down_revision: Union[str, Sequence[str], None] = "0005_alcohol"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pace_users", sa.Column("display_name", sa.String(length=255), nullable=True))
    op.add_column("pace_users", sa.Column("avatar_url", sa.String(length=2048), nullable=True))
    op.create_index("ix_pace_users_email", "pace_users", ["email"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_pace_users_email", table_name="pace_users")
    op.drop_column("pace_users", "avatar_url")
    op.drop_column("pace_users", "display_name")

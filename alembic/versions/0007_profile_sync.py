"""Durable per-account receipts for idempotent profile sync."""
from alembic import op
import sqlalchemy as sa
revision = "0007_profile_sync"
down_revision = "0006_authentication"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("pace_sync_receipts",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("pace_users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("mutation_id", sa.Uuid(), primary_key=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("response", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade():
    op.drop_table("pace_sync_receipts")

"""Alcohol record synchronization and durable tombstones."""
from alembic import op
import sqlalchemy as sa
revision = "0010_alcohol_sync"
down_revision = "0009_training_sync"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("alcohol_sync_records",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("pace_users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("entity", sa.String(16), primary_key=True),
        sa.Column("client_id", sa.String(180), primary_key=True),
        sa.Column("version", sa.BigInteger(), nullable=False),
        sa.Column("data", sa.JSON(none_as_null=True), nullable=True))


def downgrade():
    op.drop_table("alcohol_sync_records")

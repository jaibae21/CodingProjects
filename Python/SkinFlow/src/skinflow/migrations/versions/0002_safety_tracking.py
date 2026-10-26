"""Evidence-aware product tags, skin observations, and saved routine templates."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "products", sa.Column("safety_tags", sa.JSON(), nullable=False, server_default="{}")
    )
    with op.batch_alter_table("completions") as batch:
        batch.alter_column("period", existing_type=sa.String(2), type_=sa.String(20))
    op.create_table(
        "observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("region", sa.String(120), nullable=False),
        sa.Column("condition", sa.String(40), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("photo_path", sa.Text(), nullable=False),
        sa.Column("persistent", sa.Boolean(), nullable=False),
        sa.Column("painful", sa.Boolean(), nullable=False),
        sa.Column("infection_concern", sa.Boolean(), nullable=False),
        sa.Column("resolved_on", sa.Date(), nullable=True),
        sa.CheckConstraint("severity >= 0 AND severity <= 5", name="ck_observation_severity"),
    )
    op.create_index("ix_observations_day", "observations", ["day"])
    op.create_table(
        "routine_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, unique=True),
        sa.Column("payload", sa.JSON(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("routine_templates")
    op.drop_index("ix_observations_day", table_name="observations")
    op.drop_table("observations")
    with op.batch_alter_table("products") as batch:
        batch.drop_column("safety_tags")
    with op.batch_alter_table("completions") as batch:
        batch.alter_column("period", existing_type=sa.String(20), type_=sa.String(2))

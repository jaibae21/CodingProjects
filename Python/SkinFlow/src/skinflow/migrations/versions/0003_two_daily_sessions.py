"""Persist Morning/Night plans without rewriting actual historical session records."""

from datetime import datetime, timezone

import sqlalchemy as sa
from alembic import op

from skinflow.schedule_formats import collapse_sessions_v1

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    plans = sa.table(
        "plans",
        sa.column("id", sa.Integer),
        sa.column("payload", sa.JSON),
        sa.column("version", sa.Integer),
    )
    revisions = sa.table(
        "plan_revisions",
        sa.column("payload", sa.JSON),
        sa.column("created_at", sa.DateTime),
        sa.column("description", sa.String),
    )
    for row in list(connection.execute(sa.select(plans)).mappings()):
        converted = collapse_sessions_v1(row["payload"])
        connection.execute(
            plans.update()
            .where(plans.c.id == row["id"])
            .values(payload=converted, version=row["version"] + 1)
        )
        connection.execute(
            revisions.insert().values(
                payload=converted,
                created_at=datetime.now(timezone.utc),
                description="Converted routines to Morning and Night",
            )
        )
    templates = sa.table(
        "routine_templates", sa.column("id", sa.Integer), sa.column("payload", sa.JSON)
    )
    for row in list(connection.execute(sa.select(templates)).mappings()):
        connection.execute(
            templates.update()
            .where(templates.c.id == row["id"])
            .values(payload=collapse_sessions_v1(row["payload"]))
        )


def downgrade() -> None:
    raise NotImplementedError(
        "Restore the pre-upgrade database backup to recover separate legacy sessions."
    )

"""Migrations use the application's existing connection, including in packaged builds."""

from alembic import context

from skinflow.models import Base

connection = context.config.attributes["connection"]
context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=True)
with context.begin_transaction():
    context.run_migrations()

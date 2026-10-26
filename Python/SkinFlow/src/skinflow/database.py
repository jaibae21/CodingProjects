"""SQLite lifecycle, forward migrations, and consistent database backups."""

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker


def default_data_dir() -> Path:
    override = os.environ.get("SKINFLOW_DATA_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / ".local" / "share"))) / "SkinFlow"


class Database:
    def __init__(self, path: Path):
        self.path = Path(path).resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(URL.create("sqlite", database=str(self.path)))

        @event.listens_for(self.engine, "connect")
        def configure_sqlite(connection, _record):
            # Python 3.12+ supports explicit transaction handling.
            connection.autocommit = True
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA busy_timeout=5000")
            connection.autocommit = False

        self.sessions = sessionmaker(self.engine, expire_on_commit=False)

    def migrate(self) -> None:
        config = Config()
        config.set_main_option("script_location", str(Path(__file__).parent / "migrations"))
        if self.path.exists():
            with sqlite3.connect(self.path) as connection:
                has_version = connection.execute(
                    "SELECT name FROM sqlite_master WHERE name='alembic_version'"
                ).fetchone()
                current = (
                    connection.execute("SELECT version_num FROM alembic_version").fetchone()
                    if has_version
                    else None
                )
            if current and current[0] != ScriptDirectory.from_config(config).get_current_head():
                stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f")
                self.backup(self.path.with_name(f"skinflow-pre-upgrade-{stamp}.db"))
        with self.engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")

    def backup(self, destination: Path) -> None:
        destination = Path(destination).resolve()
        if destination == self.path:
            raise ValueError("Choose a backup file different from the active database.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as source, sqlite3.connect(destination) as target:
            source.backup(target)

    def close(self) -> None:
        self.engine.dispose()

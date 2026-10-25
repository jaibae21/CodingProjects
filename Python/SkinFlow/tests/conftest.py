import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from skinflow.database import Database  # noqa: E402
from skinflow.seed import seed  # noqa: E402
from skinflow.services import InventoryService, ScheduleService  # noqa: E402


@pytest.fixture(autouse=True)
def fail_on_unexpected_dialog(monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    def fail(_parent, title, message, *_args, **_kwargs):
        pytest.fail(f"Unexpected GUI dialog: {title}: {message}")

    monkeypatch.setattr(QMessageBox, "warning", fail)
    monkeypatch.setattr(QMessageBox, "critical", fail)


@pytest.fixture
def db(tmp_path):
    database = Database(tmp_path / "skinflow.db")
    database.migrate()
    seed(database)
    yield database
    database.close()


@pytest.fixture
def inventory(db):
    return InventoryService(db)


@pytest.fixture
def schedule(db):
    return ScheduleService(db)

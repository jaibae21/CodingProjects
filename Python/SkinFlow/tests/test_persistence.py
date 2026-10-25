import socket
from datetime import date

import pytest
from sqlalchemy import inspect, text

from skinflow.database import Database
from skinflow.seed import seed
from skinflow.services import InventoryService, ScheduleService, SettingsService, empty_routine


def test_restart_runs_migrations_and_retains_edits(tmp_path):
    path = tmp_path / "restart.db"
    first = Database(path)
    first.migrate()
    seed(first)
    inventory, schedule = InventoryService(first), ScheduleService(first)
    product = inventory.list()[0]
    inventory.save({"notes": "Saved before restart"}, product.id)
    day = date(2026, 10, 26)
    schedule.mark(day, "AM", schedule.routine(day, "AM")["steps"][0], True)
    schedule.set_routine(day, "PM", empty_routine(), weekly=False)
    SettingsService(first).set("theme", "dark")
    first.close()
    second = Database(path)
    try:
        second.migrate()
        seed(second)
        assert len(InventoryService(second).list()) == 24
        assert InventoryService(second).get(product.id).notes == "Saved before restart"
        assert ScheduleService(second).routine(day, "PM")["steps"] == []
        assert len(ScheduleService(second).history()) == 1
        assert SettingsService(second).get("theme") == "dark"
        with second.engine.connect() as connection:
            assert connection.scalar(text("SELECT version_num FROM alembic_version")) == "0001"
            assert connection.scalar(text("PRAGMA foreign_keys")) == 1
    finally:
        second.close()


def test_backup_is_consistent_and_can_be_opened(db, tmp_path, inventory):
    product = inventory.list()[0]
    inventory.save({"notes": "Backed up"}, product.id)
    backup_path = tmp_path / "backup.db"
    db.backup(backup_path)
    backup = Database(backup_path)
    try:
        backup.migrate()
        assert InventoryService(backup).get(product.id).notes == "Backed up"
        assert len(inspect(backup.engine).get_table_names()) == 6
    finally:
        backup.close()
    with pytest.raises(ValueError, match="different"):
        db.backup(db.path)


def test_offline_services_never_open_network_connections(monkeypatch, tmp_path):
    def blocked(*_args, **_kwargs):
        raise AssertionError("Unexpected network request")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    database = Database(tmp_path / "offline.db")
    try:
        database.migrate()
        seed(database)
        assert len(InventoryService(database).list()) == 24
        assert len(ScheduleService(database).week(date(2026, 10, 25))) == 7
    finally:
        database.close()

import json
from datetime import date
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import MetaData, Table, insert, select, text

import skinflow
from skinflow.database import Database
from skinflow.models import Completion, PlanRevision, Product
from skinflow.seed import seed
from skinflow.services import InventoryService, ScheduleService, new_step
from skinflow.tracking import ObservationService


def test_upgrade_from_phase1_backs_up_and_preserves_products_plans_completions(tmp_path):
    db = Database(tmp_path / "legacy.db")
    config = Config()
    config.set_main_option("script_location", str(Path(skinflow.__file__).parent / "migrations"))
    with db.engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "0001")
        # Reflect the old schema so current model defaults cannot mask upgrade defects.
        metadata = MetaData()
        products = Table("products", metadata, autoload_with=connection)
        values = {column.name: "" for column in products.columns}
        values.update(
            id=1,
            brand="Custom",
            name="My edited cleanser",
            category="Cleanser",
            ingredients_verified=False,
            date_added=date(2026, 10, 20),
            opened_on=None,
            expires_on=None,
            status="Active",
            deleted=False,
            notes="Keep my personal notes",
        )
        connection.execute(insert(products).values(**values))
        original_step = new_step("Historical cleanser label", 1)
        payload = {
            "weekly": {"1:PM": {"shower": True, "steps": [original_step]}},
            "monthly": [],
            "overrides": {},
        }
        connection.execute(
            text("INSERT INTO plans(id, version, payload) VALUES (1, 1, :payload)"),
            {"payload": json.dumps(payload)},
        )
        connection.execute(
            text(
                "INSERT INTO plan_revisions(id, created_at, description, payload) "
                "VALUES (1, '2026-10-25 10:00:00', 'Original', :payload)"
            ),
            {"payload": json.dumps(payload)},
        )
        connection.execute(
            text(
                "INSERT INTO completions(day, period, step_id, product_id, label, completed_at) "
                "VALUES ('2026-10-27', 'PM', :step, 1, 'Historical cleanser label', "
                "'2026-10-27 21:00:00')"
            ),
            {"step": original_step["id"]},
        )
        connection.execute(text("INSERT INTO settings(key, value) VALUES ('seed_version', '1')"))
    db.migrate()
    backups = list(tmp_path.glob("skinflow-pre-upgrade-*.db"))
    assert len(backups) == 1
    assert ObservationService(db).list() == []
    seed(db)
    assert len(InventoryService(db).list()) == 1  # Never recreate deleted/missing old products.
    assert InventoryService(db).get(1).notes == "Keep my personal notes"
    schedule = ScheduleService(db)
    assert len(schedule.history()) == 1
    assert (
        schedule.completed(date(2026, 10, 27), "Night")[original_step["id"]].label
        == "Historical cleanser label"
    )
    with db.sessions() as session:
        assert session.get(PlanRevision, 1).payload == payload
        assert session.get(Product, 1).safety_tags == {}
        assert session.scalar(select(Completion)).period == "PM"
    previous = next(
        t for t in schedule.templates() if t.name == "Saved plan before current routine"
    )
    proposed, version = schedule.template_preview(previous.id)
    schedule.apply_preview(proposed, version, "Restore my pre-upgrade edits")
    assert schedule.routine(date(2026, 10, 27), "Night")["steps"][0]["id"] == original_step["id"]
    schedule.mark(date(2026, 10, 27), "Night", original_step, False)
    assert not schedule.history()
    db.migrate()
    assert len(list(tmp_path.glob("skinflow-pre-upgrade-*.db"))) == 1
    db.close()

from copy import deepcopy
from datetime import date, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select

import skinflow
from skinflow.database import Database
from skinflow.models import Completion, Plan, PlanRevision, RoutineTemplate
from skinflow.schedule_formats import collapse_sessions_v1
from skinflow.seed import seed
from skinflow.services import ScheduleService, empty_routine, new_step


def routine(*labels, shower=False):
    return {"shower": shower, "steps": [new_step(label) for label in labels]}


def old_plan() -> dict:
    return {
        "weekly": {
            "0:AM": routine("Morning"),
            "0:Midday": routine("Midday step"),
            "0:Evening": routine("Evening step"),
            "0:Night": routine("Night step", shower=True),
        },
        "monthly": [],
        "overrides": {},
        "scalp": {},
        "scalp_overrides": {},
        "monthly_decisions": {},
    }


def test_conversion_merges_order_and_shower_flag_without_losing_or_duplicating_steps():
    legacy = old_plan()
    original = deepcopy(legacy)
    legacy["weekly"]["0:Night"]["steps"].insert(
        0, deepcopy(legacy["weekly"]["0:Evening"]["steps"][0])
    )
    converted = collapse_sessions_v1(legacy)
    night = converted["weekly"]["0:Night"]
    assert [s["label"] for s in night["steps"]] == ["Midday step", "Evening step", "Night step"]
    assert night["shower"] and night["session_merge_review"]
    assert len(converted["weekly"]) == 14
    assert converted["weekly"]["0:AM"] == original["weekly"]["0:AM"]
    assert collapse_sessions_v1(converted) == converted
    assert len(legacy["weekly"]) == 4  # Input was not normalized in place.


def test_empty_date_override_preserves_other_old_sessions():
    legacy = old_plan()
    legacy["overrides"]["2026-10-26:Evening"] = empty_routine()
    converted = collapse_sessions_v1(legacy)
    assert [s["label"] for s in converted["overrides"]["2026-10-26:Night"]["steps"]] == [
        "Midday step",
        "Night step",
    ]


def test_old_monthly_replacement_preserves_the_other_merged_sessions(schedule):
    legacy = old_plan()
    legacy["monthly"] = [
        {
            "id": "treatment",
            "name": "Monthly treatment",
            "weekday": 0,
            "ordinal": 4,
            "period": "Evening",
            "enabled": True,
            "mode": "replace",
            "routine": routine("Replacement treatment"),
        }
    ]
    converted = collapse_sessions_v1(legacy)
    result = schedule.routine(date(2026, 10, 26), "Night", converted)
    assert [s["label"] for s in result["steps"]] == [
        "Midday step",
        "Replacement treatment",
        "Night step",
    ]


@pytest.fixture
def legacy_db(tmp_path):
    db = Database(tmp_path / "legacy-four-session.db")
    config = Config()
    config.set_main_option("script_location", str(Path(skinflow.__file__).parent / "migrations"))
    with db.engine.begin() as connection:
        config.attributes["connection"] = connection
        command.upgrade(config, "0002")
    seed(db)
    with db.sessions.begin() as session:
        plan = session.get(Plan, 1)
        legacy = deepcopy(plan.payload)
        legacy.pop("session_format")
        legacy["weekly"]["5:Evening"] = legacy["weekly"].pop("5:Night")
        legacy["weekly"]["6:Midday"] = legacy["weekly"].pop("6:Night")
        for group in ("weekly", "scalp"):
            for day in range(7):
                for period in ("AM", "Midday", "Evening", "Night"):
                    legacy[group].setdefault(f"{day}:{period}", empty_routine())
        legacy["monthly"][0]["period"] = "Evening"
        plan.payload = legacy
        session.add(PlanRevision(description="Saved four-session plan", payload=deepcopy(legacy)))
        for template in session.scalars(select(RoutineTemplate)):
            template.payload = deepcopy(legacy)
    yield db
    db.close()


def test_upgrade_keeps_actual_times_labels_history_and_templates(legacy_db):
    db = legacy_db
    day = date(2026, 11, 1)
    with db.sessions.begin() as session:
        before = deepcopy(session.get(Plan, 1).payload)
        step = before["weekly"]["6:Midday"]["steps"][2]
        session.add(
            Completion(
                day=day,
                period="Midday",
                step_id=step["id"],
                product_id=step["product_id"],
                label=step["label"],
                completed_at=datetime(2026, 11, 1, 12, 34),
            )
        )
        old_version = session.get(Plan, 1).version
    db.migrate()
    schedule = ScheduleService(db)
    assert schedule.snapshot()[1] == old_version + 1
    assert len(schedule.snapshot()[0]["weekly"]) == 14
    assert "Sungboon" in schedule.routine(day, "Night")["steps"][2]["label"]
    record = schedule.completed(day, "Night")[step["id"]]
    assert record.period == "Midday" and record.completed_at == datetime(2026, 11, 1, 12, 34)
    assert record.label == step["label"]
    assert schedule.revisions()[1].payload == before
    assert all(len(t.payload["weekly"]) == 14 for t in schedule.templates())
    assert list(db.path.parent.glob("skinflow-pre-upgrade-*.db"))
    unchanged = schedule.snapshot()
    seed(db)
    db.migrate()
    assert schedule.snapshot() == unchanged


def test_restore_legacy_revision_still_exposes_only_two_sessions(legacy_db):
    db = legacy_db
    with db.sessions() as session:
        revision = session.scalar(
            select(PlanRevision).where(PlanRevision.description == "Saved four-session plan")
        )
    db.migrate()
    schedule = ScheduleService(db)
    schedule.rollback(revision.id)
    assert all(key.rsplit(":", 1)[1] in ("AM", "Night") for key in schedule.snapshot()[0]["weekly"])
    assert "Sungboon" in schedule.routine(date(2026, 11, 1), "Night")["steps"][2]["label"]


def test_approved_monthly_recovery_can_still_be_skipped_after_upgrade(legacy_db):
    db = legacy_db
    key = "monthly-aha-review:2026-11-07"
    with db.sessions.begin() as session:
        plan = session.get(Plan, 1)
        legacy = deepcopy(plan.payload)
        treatment = deepcopy(legacy["monthly"][0]["routine"])
        treatment["recovery_for"] = key
        legacy["overrides"]["2026-11-07:Evening"] = treatment
        recovery = deepcopy(legacy["weekly"]["6:Midday"])
        recovery["steps"].pop(2)  # Remove the Sunday retinoid from the approved recovery plan.
        recovery["recovery_for"] = key
        legacy["overrides"]["2026-11-08:Midday"] = recovery
        legacy["monthly_decisions"][key] = {
            "status": "approved",
            "previous_overrides": {"2026-11-07:Evening": None, "2026-11-08:Midday": None},
        }
        plan.payload = legacy
    db.migrate()
    schedule = ScheduleService(db)
    assert not any(
        "Sungboon" in s["label"] for s in schedule.routine(date(2026, 11, 8), "Night")["steps"]
    )
    payload, version = schedule.monthly_preview("monthly-aha-review", date(2026, 11, 7), False)
    schedule.apply_preview(payload, version, "Skip after session conversion")
    assert not schedule.snapshot()[0]["overrides"]
    assert "White Rice" in schedule.routine(date(2026, 11, 7), "Night")["steps"][1]["label"]
    assert "Sungboon" in schedule.routine(date(2026, 11, 8), "Night")["steps"][2]["label"]

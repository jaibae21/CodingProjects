from copy import deepcopy
from datetime import date, timedelta

import pytest

from skinflow.safety.service import SafetyService
from skinflow.seed import seed
from skinflow.services import PERIODS, empty_routine, new_step


def test_current_configuration_is_seeded_once_with_two_periods_and_separate_scalp(db, schedule):
    original = schedule.snapshot()
    seed(db)
    assert schedule.snapshot() == original
    assert len(original[0]["weekly"]) == 14
    assert len(original[0]["scalp"]) == 14
    day = date(2026, 10, 27)
    face = schedule.routine(day, "Night")
    scalp = schedule.routine(day, "Night", area="Scalp")
    assert len(face["steps"]) == 4 and len(scalp["steps"]) == 3
    assert "Nourishing Pads" in face["steps"][1]["label"]
    assert "Scalp Ampoule" in scalp["steps"][-1]["label"]
    assert scalp["steps"][-1]["region"] == "Scalp"
    assert not any(s["optional"] for s in face["steps"])
    assert all("if tolerated" not in s["label"] for s in face["steps"])


def test_current_substitutions_and_sunday_replacement(schedule, inventory):
    saturday = schedule.routine(date(2026, 10, 31), "Night")
    mask = saturday["steps"][1]
    assert "White Rice" in mask["label"] and len(mask["substitutions"]) == 2
    sunday = schedule.routine(date(2026, 11, 1), "Night")
    assert "Sungboon" in sunday["steps"][2]["label"]
    assert "dry skin" in sunday["steps"][2]["instructions"]
    assert not any("Resurfacing" in s["label"] for s in sunday["steps"])
    assert inventory.list(search="Resurfacing Retinol")


def test_monthly_peel_is_review_only_until_explicit_commit(schedule, inventory):
    saturday = date(2026, 11, 7)
    acid_id = inventory.list(search="Peeling Serum")[0].id
    before = schedule.snapshot()
    assert acid_id not in [s["product_id"] for s in schedule.routine(saturday, "Night")["steps"]]
    payload, version = schedule.monthly_preview("monthly-aha-review", saturday, True)
    assert schedule.snapshot() == before
    proposed = schedule.routine(saturday, "Night", payload)
    assert [s["product_id"] for s in proposed["steps"]][1] == acid_id
    assert not any("Mask" in s["label"] for s in proposed["steps"])
    schedule.apply_preview(payload, version, "Approved monthly treatment")
    assert schedule.routine(saturday, "Night")["steps"] == proposed["steps"]
    assert acid_id not in [
        s["product_id"] for s in schedule.routine(date(2026, 12, 5), "Night")["steps"]
    ]


def test_monthly_approval_recovery_overrides_and_skip_do_not_reschedule_actives(schedule):
    saturday = date(2026, 11, 7)
    baseline = deepcopy(schedule.snapshot()[0]["weekly"])
    thursday, sunday = saturday - timedelta(days=2), saturday + timedelta(days=1)
    actual = schedule.routine(thursday, "Night")["steps"][1]
    schedule.mark(thursday, "Night", actual, True)
    payload, version = schedule.monthly_preview("monthly-aha-review", saturday, True)
    schedule.apply_preview(payload, version, "Approved")
    assert not any(
        "Nourishing Pads" in s["label"] for s in schedule.routine(thursday, "Night")["steps"]
    )
    assert not any("Retinol" in s["label"] for s in schedule.routine(sunday, "Night")["steps"])
    assert schedule.routine(thursday, "Night", area="Scalp")["steps"]
    assert actual["id"] in schedule.completed(thursday, "Night")
    assert schedule.snapshot()[0]["weekly"] == baseline
    payload, version = schedule.monthly_preview("monthly-aha-review", saturday, False)
    schedule.apply_preview(payload, version, "Skipped")
    assert not schedule.snapshot()[0]["overrides"]
    assert any("White Rice" in s["label"] for s in schedule.routine(saturday, "Night")["steps"])
    assert not any(s["review"] for s in schedule.routine(saturday, "Night")["steps"])
    assert actual["id"] in schedule.completed(thursday, "Night")


def test_skipping_approved_monthly_preserves_later_manual_edits(schedule):
    saturday = date(2026, 11, 7)
    sunday = saturday + timedelta(days=1)
    payload, version = schedule.monthly_preview("monthly-aha-review", saturday, True)
    schedule.apply_preview(payload, version, "Approved")
    custom = {"shower": False, "steps": [new_step("My custom Sunday")]}
    schedule.set_routine(sunday, "Night", custom, weekly=False)
    payload, version = schedule.monthly_preview("monthly-aha-review", saturday, False)
    schedule.apply_preview(payload, version, "Skipped")
    assert schedule.routine(sunday, "Night")["steps"] == custom["steps"]


def test_scalp_move_does_not_duplicate_or_move_facial_retinoids(schedule):
    tuesday, wednesday = date(2026, 10, 27), date(2026, 10, 28)
    before = {day: schedule.routine(day, "Night")["steps"] for day in (tuesday, wednesday)}
    payload, version = schedule.preview_move(tuesday, wednesday, "Night", "Scalp")
    assert schedule.routine(tuesday, "Night", area="Scalp")["steps"]
    schedule.apply_preview(payload, version, "Moved shower/scalp")
    assert not schedule.routine(tuesday, "Night", area="Scalp")["steps"]
    assert schedule.routine(wednesday, "Night", area="Scalp")["steps"]
    for day in (tuesday, wednesday):
        assert schedule.routine(day, "Night")["steps"] == before[day]
    assert not schedule.routine(tuesday, "Night")["shower"]
    assert schedule.routine(wednesday, "Night")["shower"]


def test_recovery_is_a_proposal_and_stale_approval_cannot_overwrite(schedule):
    day = date(2026, 10, 27)
    before = schedule.snapshot()
    payload, version = schedule.recovery_preview(day)
    assert schedule.snapshot() == before
    assert not any(
        "Nourishing Pads" in s["label"] for s in schedule.routine(day, "Night", payload)["steps"]
    )
    schedule.set_routine(day, "AM", empty_routine(), weekly=False)
    with pytest.raises(ValueError, match="changed"):
        schedule.apply_preview(payload, version, "Stale recovery")


def test_recovery_keeps_sunscreen_last(schedule):
    day = date(2026, 10, 27)
    payload, _version = schedule.recovery_preview(day)
    steps = schedule.routine(day, "AM", payload)["steps"]
    assert "SPF 30+" in steps[-1]["label"]
    assert "Moisturizing Lotion" in steps[-2]["label"]


def test_moved_active_is_reviewed_against_neighbors_without_mutating_on_preview(schedule, db):
    tuesday, thursday = date(2026, 10, 27), date(2026, 10, 29)
    before = schedule.snapshot()
    payload, _version = schedule.preview_move(tuesday, thursday - timedelta(days=1), "Night")
    findings = SafetyService(db).review(thursday - timedelta(days=1), thursday, payload)
    assert any(f.rule_id == "active_spacing" for f in findings)
    assert schedule.snapshot() == before


def test_original_baseline_can_be_restored_without_erasing_current_template(schedule):
    templates = schedule.templates()
    original = next(t for t in templates if t.name == "Original baseline")
    payload, version = schedule.template_preview(original.id)
    day = date(2026, 10, 27)
    step = schedule.routine(day, "Night")["steps"][0]
    schedule.mark(day, "Night", step, True)
    schedule.apply_preview(payload, version, "Restored original")
    assert len(schedule.history()) == 1
    assert len(schedule.templates()) == 3
    assert all(f"0:{period}" in schedule.snapshot()[0]["weekly"] for period in PERIODS)

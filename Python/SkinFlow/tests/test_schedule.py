from copy import deepcopy
from datetime import date, timedelta

import pytest

from skinflow.services import empty_routine, new_step


def test_current_week_starts_on_monday_and_preserves_application_order(schedule):
    week = schedule.week(date(2026, 10, 29))
    assert len(week) == 7
    assert week[0][0] == date(2026, 10, 26)
    assert week[-1][0] == date(2026, 11, 1)
    for day, am, night in week:
        assert "Gentle Skin Cleanser" in am["steps"][0]["label"]
        assert "SPF 30+" in am["steps"][-1]["label"]
        assert night["shower"] == (day.weekday() in (1, 3))
    assert "MISSHA" in week[2][2]["steps"][0]["label"]
    assert "Sungboon" in week[-1][2]["steps"][2]["label"]
    assert "Klairs" in week[5][2]["steps"][-1]["label"]
    assert all(len(entry) == 3 for entry in week)


@pytest.mark.parametrize(
    "day,has_review",
    [
        (date(2026, 11, 7), True),
        (date(2026, 11, 14), False),
        (date(2026, 12, 5), True),
        (date(2027, 1, 2), True),
    ],
)
def test_first_saturday_is_review_only(schedule, day, has_review):
    steps = schedule.routine(day, "Night")["steps"]
    reviews = [s for s in steps if s["review"]]
    assert bool(reviews) is has_review
    if has_review:
        assert reviews[0]["product_id"] is None
        assert "REVIEW / OPTIONAL" in reviews[0]["label"]


def test_weekly_edit_and_one_off_override_have_distinct_scopes(schedule):
    day = date(2026, 10, 27)
    one_off = {"shower": False, "steps": [new_step("Recovery reminder")]}
    baseline = schedule.routine(day, "PM")
    schedule.set_routine(day, "PM", one_off, weekly=False)
    assert schedule.routine(day, "PM")["overridden"]
    assert schedule.routine(day + timedelta(days=7), "PM") == baseline
    schedule.set_routine(day, "PM", empty_routine(), weekly=True)
    assert schedule.routine(day + timedelta(days=7), "PM")["steps"] == []
    assert schedule.routine(day, "PM")["steps"] == one_off["steps"]
    schedule.clear_override(day, "PM")
    assert schedule.routine(day, "PM")["steps"] == []


def test_override_replaces_monthly_steps_too(schedule):
    day = date(2026, 11, 7)
    schedule.set_routine(day, "Night", empty_routine(), weekly=False)
    assert not schedule.routine(day, "Night")["steps"]
    schedule.clear_override(day, "Night")
    assert any(s["review"] for s in schedule.routine(day, "Night")["steps"])


def test_move_preserves_baseline_and_actual_completions(schedule):
    source, target = date(2026, 10, 27), date(2026, 10, 28)
    original = schedule.routine(source, "PM")
    step = original["steps"][0]
    schedule.mark(source, "PM", step, True)
    schedule.move(source, target, "PM")
    assert not schedule.routine(source, "PM")["steps"]
    assert schedule.routine(target, "PM")["steps"] == original["steps"]
    assert schedule.routine(target, "PM")["shower"]
    assert schedule.routine(source + timedelta(days=7), "PM")["steps"] == original["steps"]
    assert step["id"] in schedule.completed(source, "PM")
    assert not schedule.completed(target, "PM")


def test_rollback_restores_all_schedule_scopes_without_touching_completions(schedule):
    original = schedule.snapshot()[0]
    initial_revision = schedule.revisions()[0].id
    count = len(schedule.revisions())
    day = date(2026, 10, 26)
    schedule.mark(day, "AM", schedule.routine(day, "AM")["steps"][0], True)
    schedule.set_routine(day, "AM", empty_routine(), weekly=False)
    schedule.save_monthly([], schedule.snapshot()[1])
    schedule.rollback(initial_revision)
    assert schedule.snapshot()[0] == original
    assert len(schedule.history()) == 1
    assert len(schedule.revisions()) == count + 3
    assert "Rolled back" in schedule.revisions()[0].description


def test_stale_edit_is_rejected(schedule):
    version = schedule.snapshot()[1]
    day = date(2026, 10, 26)
    schedule.set_routine(day, "AM", empty_routine(), weekly=True)
    with pytest.raises(ValueError, match="changed"):
        schedule.set_routine(day, "AM", empty_routine(), weekly=False, expected_version=version)
    assert not schedule.snapshot()[0]["overrides"]


def test_monthly_recurrence_can_be_edited_and_disabled(schedule):
    payload, version = schedule.snapshot()
    rule = deepcopy(payload["monthly"][0])
    rule.update(ordinal=2, weekday=2, period="AM")
    schedule.save_monthly([rule], version)
    day = date(2026, 11, 11)
    assert len(schedule.routine(day, "AM")["steps"]) == 4
    rule["enabled"] = False
    schedule.save_monthly([rule], schedule.snapshot()[1])
    assert len(schedule.routine(day, "AM")["steps"]) == 3


def test_completion_is_idempotent_and_can_be_unchecked(schedule):
    day = date(2026, 10, 26)
    step = schedule.routine(day, "AM")["steps"][0]
    schedule.mark(day, "AM", step, True)
    schedule.mark(day, "AM", step, True)
    assert len(schedule.completed(day, "AM")) == 1
    schedule.mark(day, "AM", step, False)
    assert not schedule.history()


def test_invalid_routine_does_not_create_revision(schedule):
    day = date(2026, 10, 26)
    version = schedule.snapshot()[1]
    step = new_step("Same ID")
    with pytest.raises(ValueError, match="distinct"):
        schedule.set_routine(day, "AM", {"shower": False, "steps": [step, step]}, weekly=False)
    assert schedule.snapshot()[1] == version


def test_next_treatment_skips_earlier_period_and_generic_sunscreen_reminders(schedule):
    sunday = date(2026, 10, 25)
    upcoming = schedule.next_treatment(sunday, "Night")
    assert upcoming[0] == sunday
    assert "Night" in upcoming[1] and "Sungboon" in upcoming[1]
    payload, _version = schedule.snapshot()
    for key, routine in payload["weekly"].items():
        routine["steps"] = [step for step in routine["steps"] if step["product_id"] is None]
    schedule._save(payload, schedule.snapshot()[1], "Only reminders")
    upcoming = schedule.next_treatment(sunday)
    assert upcoming[0] == date(2026, 11, 7)
    assert "REVIEW / OPTIONAL" in upcoming[1]

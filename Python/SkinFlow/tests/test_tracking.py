from datetime import date, timedelta

import pytest

from skinflow.tracking import ObservationService, care_guidance

DAY = date(2026, 10, 25)


def test_observation_create_edit_resolve_and_history(db):
    service = ObservationService(db)
    row = service.save(
        {
            "day": DAY,
            "region": "Eyebrows",
            "condition": "Stinging/Burning",
            "severity": 2,
            "notes": "After pads",
            "photo_path": "local-photo.jpg",
        }
    )
    assert service.active(DAY)[0].id == row.id
    assert "push through" in care_guidance(row)
    service.save({"notes": "Updated notes", "painful": True}, row.id)
    assert "professional evaluation" in care_guidance(service.list()[0])
    service.resolve(row.id, DAY + timedelta(days=1))
    assert service.active(DAY)
    assert not service.active(DAY + timedelta(days=1))
    assert service.list()[0].notes == "Updated notes"
    assert service.list()[0].photo_path == "local-photo.jpg"
    service.delete(row.id)
    assert not service.list()


def test_latest_state_per_region_clears_older_states_and_future_states_do_not_leak(db):
    service = ObservationService(db)
    for day, condition in (
        (DAY, "Red/Irritated"),
        (DAY + timedelta(days=1), "Normal"),
        (DAY + timedelta(days=3), "Dry"),
    ):
        service.save({"day": day, "region": "Eyebrows", "condition": condition, "severity": 1})
    assert service.active(DAY)[0].condition == "Red/Irritated"
    assert not service.active(DAY + timedelta(days=2))
    assert service.active(DAY + timedelta(days=3))[0].condition == "Dry"


@pytest.mark.parametrize(
    "changes",
    [
        {"severity": 6},
        {"severity": -1},
        {"severity": True},
        {"region": " "},
        {"condition": "Diagnosis"},
        {"resolved_on": DAY - timedelta(days=1)},
    ],
)
def test_invalid_observations_are_rejected_atomically(db, changes):
    service = ObservationService(db)
    data = {"day": DAY, "region": "Face", "condition": "Dry", "severity": 1}
    with pytest.raises(ValueError):
        service.save({**data, **changes})
    assert not service.list()


def test_timeline_uses_only_actual_completions(db, schedule):
    service = ObservationService(db)
    assert not service.nearby_completions(DAY)
    step = schedule.routine(DAY, "Night")["steps"][2]
    schedule.mark(DAY, "Night", step, True)
    assert service.nearby_completions(DAY + timedelta(days=2))[0].label == step["label"]
    assert not service.nearby_completions(DAY + timedelta(days=4))

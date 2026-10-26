"""Local observations and temporal context without medical causal inference."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select

from skinflow.database import Database
from skinflow.models import Completion, Observation

CONDITIONS = (
    "Normal",
    "Dry",
    "Red/Irritated",
    "Stinging/Burning",
    "Active Acne",
    "Recovering",
    "Other",
)
REGIONS = ("Face", "Eyebrows", "Forehead", "Cheeks", "Nose", "Chin", "Neck", "Body", "Scalp")
OBSERVATION_FIELDS = {
    "day",
    "region",
    "condition",
    "severity",
    "notes",
    "photo_path",
    "persistent",
    "painful",
    "infection_concern",
    "resolved_on",
}


def care_guidance(observation: Observation) -> str:
    if observation.condition == "Normal":
        return ""
    if (
        observation.persistent
        or observation.painful
        or observation.infection_concern
        or observation.severity >= 4
    ):
        return (
            "Seek professional evaluation for persistent, severe, painful, possibly infected, "
            "or otherwise concerning symptoms. This log cannot diagnose the cause."
        )
    if observation.condition == "Stinging/Burning":
        return (
            "Do not push through stinging or burning. Avoid the suspected product on the "
            "affected area and seek professional advice if symptoms persist or concern you."
        )
    return "If symptoms persist, worsen, or concern you, seek professional evaluation."


class ObservationService:
    def __init__(self, database: Database):
        self.db = database

    def list(self, start: date | None = None, end: date | None = None) -> list[Observation]:
        with self.db.sessions() as session:
            query = select(Observation)
            if start:
                query = query.where(Observation.day >= start)
            if end:
                query = query.where(Observation.day <= end)
            return list(
                session.scalars(query.order_by(Observation.day.desc(), Observation.id.desc()))
            )

    def save(self, data: dict, observation_id: int | None = None) -> Observation:
        if set(data) - OBSERVATION_FIELDS:
            raise ValueError("Unknown observation fields.")
        with self.db.sessions.begin() as session:
            row = session.get(Observation, observation_id) if observation_id else Observation()
            if row is None:
                raise ValueError("Observation not found.")
            for key, value in data.items():
                setattr(row, key, value.strip() if isinstance(value, str) else value)
            if type(row.day) is not date:
                raise ValueError("Choose an observation date.")
            if not row.region or len(row.region) > 120:
                raise ValueError("Enter an affected region (up to 120 characters).")
            if row.condition not in CONDITIONS:
                raise ValueError("Choose a skin condition.")
            if type(row.severity) is not int or not 0 <= row.severity <= 5:
                raise ValueError("Severity must be an integer from 0 to 5.")
            if row.resolved_on and row.resolved_on < row.day:
                raise ValueError("Resolution cannot precede the observation.")
            session.add(row)
            session.flush()
            return row

    def resolve(self, observation_id: int, day: date) -> None:
        self.save({"resolved_on": day}, observation_id)

    def delete(self, observation_id: int) -> None:
        with self.db.sessions.begin() as session:
            row = session.get(Observation, observation_id)
            if row is None:
                raise ValueError("Observation not found.")
            session.delete(row)

    def active(self, day: date) -> list[Observation]:
        # The latest state per region wins; a Normal/resolved entry clears older states.
        latest: dict[str, Observation] = {}
        for row in self.list(end=day):
            latest.setdefault(row.region.casefold(), row)
        return [
            row
            for row in latest.values()
            if row.condition != "Normal" and (row.resolved_on is None or row.resolved_on > day)
        ]

    def nearby_completions(self, day: date, days_before: int = 3) -> list[Completion]:
        with self.db.sessions() as session:
            return list(
                session.scalars(
                    select(Completion)
                    .where(
                        Completion.day >= day - timedelta(days=days_before), Completion.day <= day
                    )
                    .order_by(Completion.day, Completion.completed_at)
                )
            )

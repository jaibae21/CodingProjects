"""Read-only database adapter for the pure safety engine."""

from datetime import date, timedelta

from sqlalchemy import select

from skinflow.database import Database
from skinflow.models import Completion, Product
from skinflow.safety.engine import (
    Finding,
    ProductInfo,
    RoutineContext,
    SafetyPolicy,
    SkinState,
    evaluate,
)
from skinflow.services import PERIODS, ScheduleService, SettingsService, canonical_period
from skinflow.tracking import ObservationService


class SafetyService:
    def __init__(self, database: Database):
        self.db = database
        self.schedule = ScheduleService(database)
        self.observations = ObservationService(database)

    def policy(self) -> SafetyPolicy:
        settings = SettingsService(self.db)
        return SafetyPolicy(
            int(settings.get("active_gap_hours", "48")),
            int(settings.get("max_exfoliation_sessions", "1")),
        )

    def review(
        self, start: date, end: date | None = None, payload: dict | None = None
    ) -> list[Finding]:
        end = end or start
        if end < start or (end - start).days > 62:
            raise ValueError("Review between 1 and 63 days at a time.")
        payload = payload if payload is not None else self.schedule.snapshot()[0]
        first, last = start - timedelta(days=7), end + timedelta(days=7)
        with self.db.sessions() as session:
            products = {
                p.id: ProductInfo(
                    p.id,
                    p.label,
                    p.category,
                    p.safety_tags,
                    not p.deleted and p.status in ("Active", "Testing"),
                    p.ingredients_verified,
                )
                for p in session.scalars(select(Product))
            }
            completions = list(
                session.scalars(
                    select(Completion).where(Completion.day >= first, Completion.day <= last)
                )
            )
        routines = []
        planned = set()
        by_slot = {}
        states = {}
        for offset in range((last - first).days + 1):
            day = first + timedelta(days=offset)
            states[day] = [
                SkinState(o.day, o.region, o.condition, o.severity)
                for o in self.observations.active(day)
            ]
            for area in ("Face", "Scalp"):
                for period in PERIODS:
                    routine = self.schedule.routine(day, period, payload, area)
                    context = RoutineContext(day, period, area, routine["steps"])
                    routines.append(context)
                    by_slot[day, period, area] = context
                    planned.update(
                        (day, period, s["id"], s.get("product_id")) for s in routine["steps"]
                    )
        # Include actual products removed from the current plan, without double-counting steps.
        for row in completions:
            period = canonical_period(row.period)
            if row.product_id and (row.day, period, row.step_id, row.product_id) not in planned:
                area = (
                    "Scalp"
                    if products.get(row.product_id) and products[row.product_id].category == "Scalp"
                    else "Face"
                )
                by_slot[row.day, period, area].steps.append(
                    {
                        "id": row.step_id,
                        "product_id": row.product_id,
                        "label": row.label,
                        "_completed": True,
                    }
                )
        return evaluate(routines, products, states, start, end, self.policy())

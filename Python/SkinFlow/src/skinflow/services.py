"""Validated inventory operations and deterministic, offline schedule management."""

from copy import deepcopy
from datetime import date, timedelta
from uuid import uuid4

from sqlalchemy import delete, select, update

from skinflow.database import Database
from skinflow.models import Completion, Plan, PlanRevision, Product, Setting

CATEGORIES = (
    "Cleanser",
    "Treatment",
    "Moisturizer",
    "Mask",
    "Targeted",
    "Scalp",
    "Sunscreen",
    "Other",
)
STATUSES = ("Active", "Testing", "Paused", "Archived")
PERIODS = ("AM", "PM")
PRODUCT_FIELDS = {column.name for column in Product.__table__.columns} - {
    "id",
    "deleted",
    "date_added",
}


def new_step(
    label: str, product_id: int | None = None, *, optional: bool = False, review: bool = False
) -> dict:
    return {
        "id": uuid4().hex,
        "label": label,
        "product_id": product_id,
        "optional": optional,
        "review": review,
    }


def empty_routine() -> dict:
    return {"shower": False, "steps": []}


class InventoryService:
    def __init__(self, database: Database):
        self.db = database

    def list(self, search: str = "", category: str = "All", status: str = "All") -> list[Product]:
        with self.db.sessions() as session:
            query = select(Product).where(Product.deleted.is_(False))
            if category != "All":
                query = query.where(Product.category == category)
            if status != "All":
                query = query.where(Product.status == status)
            products = list(session.scalars(query.order_by(Product.brand, Product.name)))
            needle = search.strip().casefold()
            return [p for p in products if needle in f"{p.label} {p.actives}".casefold()]

    def get(self, product_id: int) -> Product:
        with self.db.sessions() as session:
            product = session.get(Product, product_id)
            if product is None or product.deleted:
                raise ValueError("This product is no longer in the inventory.")
            return product

    def save(self, data: dict, product_id: int | None = None) -> Product:
        if set(data) - PRODUCT_FIELDS:
            raise ValueError("Unknown product fields.")
        values = {k: v.strip() if isinstance(v, str) else v for k, v in data.items()}
        with self.db.sessions.begin() as session:
            product = (
                session.get(Product, product_id) if product_id is not None else Product(brand="")
            )
            if product is None or product.deleted:
                raise ValueError("This product is no longer in the inventory.")
            for key, value in values.items():
                setattr(product, key, value)
            if not product.name or not product.name.strip():
                raise ValueError("Product name is required.")
            if product.category not in CATEGORIES:
                raise ValueError("Choose a supported category.")
            if (product.status or "Active") not in STATUSES:
                raise ValueError("Choose a supported product status.")
            if (product.suitability or "AM/PM") not in ("AM", "PM", "AM/PM"):
                raise ValueError("Choose AM, PM, or AM/PM suitability.")
            if product.ingredients_verified and not product.ingredients:
                raise ValueError("Enter the ingredient list before marking it verified.")
            if product.opened_on and product.expires_on and product.expires_on < product.opened_on:
                raise ValueError("Expiration cannot be earlier than the opened date.")
            session.add(product)
            session.flush()
            return product

    def archive(self, product_id: int) -> None:
        self.save({"status": "Archived"}, product_id)

    def delete(self, product_id: int) -> None:
        # A tombstone keeps references and historical records intact.
        with self.db.sessions.begin() as session:
            product = session.get(Product, product_id)
            if product is None or product.deleted:
                raise ValueError("This product is no longer in the inventory.")
            product.deleted = True


class ScheduleService:
    def __init__(self, database: Database):
        self.db = database

    def snapshot(self) -> tuple[dict, int]:
        with self.db.sessions() as session:
            plan = session.get(Plan, 1)
            if plan is None:
                raise ValueError("The baseline schedule has not been initialized.")
            return deepcopy(plan.payload), plan.version

    def _save(self, payload: dict, version: int, description: str) -> None:
        self._validate(payload)
        with self.db.sessions.begin() as session:
            result = session.execute(
                update(Plan)
                .where(Plan.id == 1, Plan.version == version)
                .values(payload=deepcopy(payload), version=version + 1)
            )
            if result.rowcount != 1:
                raise ValueError("The schedule changed in another window. Reopen the editor.")
            session.add(PlanRevision(payload=deepcopy(payload), description=description[:250]))

    @staticmethod
    def _validate(payload: dict) -> None:
        routines = list(payload["weekly"].values()) + list(payload["overrides"].values())
        for rule in payload["monthly"]:
            if rule["weekday"] not in range(7) or rule["ordinal"] not in range(1, 6):
                raise ValueError("Invalid monthly recurrence.")
            if rule["period"] not in PERIODS:
                raise ValueError("Invalid monthly period.")
            routines.append(rule["routine"])
        for routine in routines:
            ids = [step["id"] for step in routine["steps"]]
            if len(set(ids)) != len(ids):
                raise ValueError("Routine steps must have distinct IDs.")
            if any(not step["label"].strip() for step in routine["steps"]):
                raise ValueError("Each step needs a label.")

    def routine(self, day: date, period: str, payload: dict | None = None) -> dict:
        if period not in PERIODS:
            raise ValueError("Choose AM or PM.")
        payload = payload if payload is not None else self.snapshot()[0]
        override = payload["overrides"].get(f"{day.isoformat()}:{period}")
        if override is not None:
            return {**deepcopy(override), "overridden": True}
        result = deepcopy(payload["weekly"].get(f"{day.weekday()}:{period}", empty_routine()))
        for rule in payload["monthly"]:
            if (
                rule["enabled"]
                and rule["weekday"] == day.weekday()
                and rule["ordinal"] == (day.day - 1) // 7 + 1
                and rule["period"] == period
            ):
                for step in deepcopy(rule["routine"]["steps"]):
                    step["id"] = f"{rule['id']}:{step['id']}"
                    result["steps"].append(step)
                result["shower"] |= rule["routine"]["shower"]
        return {**result, "overridden": False}

    def week(self, day: date) -> list[tuple[date, dict, dict]]:
        monday = day - timedelta(days=day.weekday())
        payload, _version = self.snapshot()
        return [
            (d, self.routine(d, "AM", payload), self.routine(d, "PM", payload))
            for d in (monday + timedelta(days=i) for i in range(7))
        ]

    def set_routine(
        self,
        day: date,
        period: str,
        routine: dict,
        *,
        weekly: bool,
        expected_version: int | None = None,
    ) -> None:
        if period not in PERIODS:
            raise ValueError("Choose AM or PM.")
        payload, version = self.snapshot()
        if expected_version is not None and expected_version != version:
            raise ValueError("The schedule changed. Reopen the editor.")
        key = f"{day.weekday() if weekly else day.isoformat()}:{period}"
        payload["weekly" if weekly else "overrides"][key] = deepcopy(routine)
        scope = day.strftime("%A") if weekly else day.isoformat()
        self._save(
            payload, version, f"Edited {scope} {period} ({'weekly' if weekly else 'one-off'})"
        )

    def clear_override(self, day: date, period: str) -> None:
        payload, version = self.snapshot()
        payload["overrides"].pop(f"{day.isoformat()}:{period}", None)
        self._save(payload, version, f"Restored baseline for {day} {period}")

    def move(self, source: date, target: date, period: str) -> None:
        if source == target:
            raise ValueError("Choose a different date.")
        payload, version = self.snapshot()
        payload["overrides"][f"{target.isoformat()}:{period}"] = self.routine(
            source, period, payload
        )
        payload["overrides"][f"{target.isoformat()}:{period}"].pop("overridden", None)
        payload["overrides"][f"{source.isoformat()}:{period}"] = empty_routine()
        self._save(payload, version, f"Moved {source} {period} to {target} (replaced target)")

    def save_monthly(self, rules: list[dict], expected_version: int) -> None:
        payload, version = self.snapshot()
        if version != expected_version:
            raise ValueError("The schedule changed. Reopen the editor.")
        payload["monthly"] = deepcopy(rules)
        self._save(payload, version, "Updated monthly treatments")

    def revisions(self) -> list[PlanRevision]:
        with self.db.sessions() as session:
            return list(session.scalars(select(PlanRevision).order_by(PlanRevision.id.desc())))

    def rollback(self, revision_id: int) -> None:
        with self.db.sessions() as session:
            revision = session.get(PlanRevision, revision_id)
            if revision is None:
                raise ValueError("Schedule revision not found.")
            payload = deepcopy(revision.payload)
        self._save(payload, self.snapshot()[1], f"Rolled back to revision {revision_id}")

    def completed(self, day: date, period: str) -> dict[str, Completion]:
        with self.db.sessions() as session:
            return {
                c.step_id: c
                for c in session.scalars(
                    select(Completion).where(Completion.day == day, Completion.period == period)
                )
            }

    def mark(self, day: date, period: str, step: dict, done: bool) -> None:
        if period not in PERIODS:
            raise ValueError("Choose AM or PM.")
        with self.db.sessions.begin() as session:
            existing = session.scalar(
                select(Completion).where(
                    Completion.day == day,
                    Completion.period == period,
                    Completion.step_id == step["id"],
                )
            )
            if done and existing is None:
                session.add(
                    Completion(
                        day=day,
                        period=period,
                        step_id=step["id"],
                        label=step["label"],
                        product_id=step["product_id"],
                    )
                )
            elif not done and existing is not None:
                session.execute(delete(Completion).where(Completion.id == existing.id))

    def history(self, limit: int = 200) -> list[Completion]:
        with self.db.sessions() as session:
            return list(
                session.scalars(
                    select(Completion)
                    .order_by(Completion.day.desc(), Completion.completed_at.desc())
                    .limit(limit)
                )
            )

    def next_treatment(self, start: date, start_period: str = "AM") -> tuple[date, str] | None:
        if start_period not in PERIODS:
            raise ValueError("Choose AM or PM.")
        payload, _version = self.snapshot()
        monthly_prefixes = tuple(f"{rule['id']}:" for rule in payload["monthly"])
        with self.db.sessions() as session:
            ids = set(
                session.scalars(
                    select(Product.id).where(
                        Product.category.in_(("Treatment", "Mask")), Product.deleted.is_(False)
                    )
                )
            )
        for offset in range(62):
            day = start + timedelta(days=offset)
            for period in PERIODS:
                if offset == 0 and period == "AM" and start_period == "PM":
                    continue
                for step in self.routine(day, period, payload)["steps"]:
                    monthly_review = step["review"] and step["id"].startswith(monthly_prefixes)
                    if step["product_id"] in ids or monthly_review:
                        return day, f"{period} · {step['label']}"
        return None


class SettingsService:
    def __init__(self, database: Database):
        self.db = database

    def get(self, key: str, default: str = "") -> str:
        with self.db.sessions() as session:
            row = session.get(Setting, key)
            return row.value if row else default

    def set(self, key: str, value: str) -> None:
        with self.db.sessions.begin() as session:
            session.merge(Setting(key=key, value=value))

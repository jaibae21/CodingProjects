"""Validated inventory operations and deterministic, offline schedule management."""

from copy import deepcopy
from datetime import date, timedelta
from uuid import uuid4

from sqlalchemy import delete, select, update

from skinflow.database import Database
from skinflow.models import Completion, Plan, PlanRevision, Product, RoutineTemplate, Setting
from skinflow.safety.tags import IRRITANTS, validate_tags
from skinflow.schedule_formats import NIGHT_ALIASES, collapse_sessions_v1

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
PERIODS = ("AM", "Night")
PERIOD_LABELS = ("Morning", "Night")


def canonical_period(period: str) -> str:
    period = "Night" if period in NIGHT_ALIASES else period
    if period not in PERIODS:
        raise ValueError("Choose Morning or Night.")
    return period


def normalize_plan(payload: dict) -> dict:
    """Present legacy revisions in two sessions without rewriting their raw snapshots."""
    payload = collapse_sessions_v1(payload)
    for group in ("weekly", "scalp", "overrides", "scalp_overrides"):
        values = payload.setdefault(group, {})
        for key in list(values):
            if key.endswith(":PM"):
                values[key[:-2] + "Night"] = values.pop(key)
        if group in ("weekly", "scalp"):
            for day in range(7):
                for period in PERIODS:
                    values.setdefault(f"{day}:{period}", empty_routine())
    for rule in payload.setdefault("monthly", []):
        rule["period"] = canonical_period(rule["period"])
    payload.setdefault("monthly_decisions", {})
    return payload


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
        "instructions": "",
        "skip_conditions": "",
        "substitutions": [],
        "frequency": "As scheduled",
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
            validate_tags(product.safety_tags or {})
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
            return normalize_plan(plan.payload), plan.version

    def _save(self, payload: dict, version: int, description: str) -> None:
        payload = normalize_plan(payload)
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
        routines = [
            routine
            for group in ("weekly", "overrides", "scalp", "scalp_overrides")
            for routine in payload[group].values()
        ]
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

    def routine(
        self, day: date, period: str, payload: dict | None = None, area: str = "Face"
    ) -> dict:
        period = canonical_period(period)
        payload = payload if payload is not None else self.snapshot()[0]
        overrides = "scalp_overrides" if area == "Scalp" else "overrides"
        base = "scalp" if area == "Scalp" else "weekly"
        override = payload[overrides].get(f"{day.isoformat()}:{period}")
        if override is not None:
            return {**deepcopy(override), "overridden": True}
        result = deepcopy(payload[base].get(f"{day.weekday()}:{period}", empty_routine()))
        for rule in payload["monthly"] if area == "Face" else []:
            if (
                rule["enabled"]
                and rule["weekday"] == day.weekday()
                and rule["ordinal"] == (day.day - 1) // 7 + 1
                and rule["period"] == period
            ):
                decision = payload["monthly_decisions"].get(f"{rule['id']}:{day}", {}).get("status")
                if rule.get("requires_review") and decision != "approved":
                    if decision != "skipped":
                        result["steps"].append(
                            {
                                **new_step(f"REVIEW / OPTIONAL: {rule['name']}"),
                                "id": f"{rule['id']}:review",
                                "review": True,
                            }
                        )
                    continue
                if rule.get("mode") == "replace":
                    if "replace_step_ids" in rule:
                        removed = set(rule["replace_step_ids"])
                        insert_at = next(
                            (i for i, s in enumerate(result["steps"]) if s["id"] in removed),
                            len(result["steps"]),
                        )
                        result["steps"] = [s for s in result["steps"] if s["id"] not in removed]
                    else:
                        result = empty_routine()
                        insert_at = 0
                else:
                    insert_at = len(result["steps"])
                for step in deepcopy(rule["routine"]["steps"]):
                    step["id"] = f"{rule['id']}:{step['id']}"
                    result["steps"].insert(insert_at, step)
                    insert_at += 1
                result["shower"] |= rule["routine"]["shower"]
        return {**result, "overridden": False}

    def week(self, day: date, area: str = "Face") -> list[tuple]:
        monday = day - timedelta(days=day.weekday())
        payload, _version = self.snapshot()
        return [
            (d, *(self.routine(d, period, payload, area) for period in PERIODS))
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
        area: str = "Face",
    ) -> None:
        period = canonical_period(period)
        payload, version = self.snapshot()
        if expected_version is not None and expected_version != version:
            raise ValueError("The schedule changed. Reopen the editor.")
        key = f"{day.weekday() if weekly else day.isoformat()}:{period}"
        group = (
            ("scalp" if weekly else "scalp_overrides")
            if area == "Scalp"
            else ("weekly" if weekly else "overrides")
        )
        clean = deepcopy(routine)
        clean.pop("recovery_for", None)
        payload[group][key] = clean
        scope = day.strftime("%A") if weekly else day.isoformat()
        self._save(
            payload, version, f"Edited {scope} {period} ({'weekly' if weekly else 'one-off'})"
        )

    def clear_override(self, day: date, period: str, area: str = "Face") -> None:
        period = canonical_period(period)
        payload, version = self.snapshot()
        payload["scalp_overrides" if area == "Scalp" else "overrides"].pop(
            f"{day.isoformat()}:{period}", None
        )
        self._save(payload, version, f"Restored baseline for {day} {period}")

    def move(self, source: date, target: date, period: str, area: str = "Face") -> None:
        payload, version = self.preview_move(source, target, period, area)
        self._save(
            payload, version, f"Moved {area} {source} {period} to {target} (replaced target)"
        )

    def preview_move(
        self, source: date, target: date, period: str, area: str = "Face"
    ) -> tuple[dict, int]:
        period = canonical_period(period)
        if source == target:
            raise ValueError("Choose a different date.")
        payload, version = self.snapshot()
        group = "scalp_overrides" if area == "Scalp" else "overrides"
        payload[group][f"{target.isoformat()}:{period}"] = self.routine(
            source, period, payload, area
        )
        payload[group][f"{target.isoformat()}:{period}"].pop("overridden", None)
        payload[group][f"{source.isoformat()}:{period}"] = empty_routine()
        if area == "Scalp":
            for day, shower in ((source, False), (target, True)):
                face = self.routine(day, period, payload)
                face.pop("overridden", None)
                face["shower"] = shower
                payload["overrides"][f"{day}:{period}"] = face
        return payload, version

    def apply_preview(self, payload: dict, expected_version: int, description: str) -> None:
        """Commit only after a UI's explicit review/approval; stale versions remain rejected."""
        self._save(payload, expected_version, description)

    def templates(self) -> list[RoutineTemplate]:
        with self.db.sessions() as session:
            return list(session.scalars(select(RoutineTemplate).order_by(RoutineTemplate.id)))

    def template_preview(self, template_id: int) -> tuple[dict, int]:
        with self.db.sessions() as session:
            template = session.get(RoutineTemplate, template_id)
            if template is None:
                raise ValueError("Routine template not found.")
            payload = normalize_plan(template.payload)
        return payload, self.snapshot()[1]

    def _recovery_routine(self, routine: dict) -> dict:
        with self.db.sessions() as session:
            products = {p.id: p for p in session.scalars(select(Product))}
        result = deepcopy(routine)
        result.pop("overridden", None)
        result["name"] = "Recovery (review tolerance)"
        result["steps"] = [
            s
            for s in result["steps"]
            if s.get("product_id") not in products
            or not IRRITANTS.intersection(products[s["product_id"]].safety_tags)
        ]
        categories = {
            products[s["product_id"]].category
            for s in result["steps"]
            if s.get("product_id") in products
        }
        for category in ("Cleanser", "Moisturizer"):
            if category not in categories:
                candidate = next(
                    (
                        p
                        for p in products.values()
                        if p.category == category
                        and not p.deleted
                        and p.status == "Active"
                        and not IRRITANTS.intersection(p.safety_tags)
                    ),
                    None,
                )
                if candidate:
                    step = new_step(candidate.label, candidate.id)
                    if category == "Cleanser":
                        result["steps"].insert(0, step)
                    else:
                        sunscreen_index = next(
                            (
                                i
                                for i, s in enumerate(result["steps"])
                                if (
                                    s.get("product_id") in products
                                    and "spf30" in products[s["product_id"]].safety_tags
                                )
                                or (s.get("product_id") is None and "SPF 30+" in s["label"])
                            ),
                            len(result["steps"]),
                        )
                        result["steps"].insert(sunscreen_index, step)
        return result

    def recovery_preview(self, day: date, before: int = 0, after: int = 0) -> tuple[dict, int]:
        if not 0 <= before <= 7 or not 0 <= after <= 7:
            raise ValueError("Choose up to 7 recovery days before and after.")
        payload, version = self.snapshot()
        for offset in range(-before, after + 1):
            target = day + timedelta(days=offset)
            for period in PERIODS:
                current = self.routine(target, period, payload)
                if current["steps"]:
                    payload["overrides"][f"{target}:{period}"] = self._recovery_routine(current)
        return payload, version

    def monthly_occurrences(self, day: date) -> list[dict]:
        payload, _version = self.snapshot()
        return [
            deepcopy(rule)
            for rule in payload["monthly"]
            if rule["enabled"]
            and rule["weekday"] == day.weekday()
            and rule["ordinal"] == (day.day - 1) // 7 + 1
        ]

    def monthly_preview(self, rule_id: str, day: date, approve: bool) -> tuple[dict, int]:
        payload, version = self.snapshot()
        rule = next((r for r in self.monthly_occurrences(day) if r["id"] == rule_id), None)
        if rule is None:
            raise ValueError("No matching monthly treatment on that date.")
        key = f"{rule_id}:{day}"
        old = payload["monthly_decisions"].get(key, {})
        # Remove only the recovery overrides still owned by this treatment.
        for slot, previous in old.get("previous_overrides", {}).items():
            if payload["overrides"].get(slot, {}).get("recovery_for") == key:
                if previous is None:
                    payload["overrides"].pop(slot, None)
                else:
                    payload["overrides"][slot] = previous
        decision = {"status": "approved" if approve else "skipped", "previous_overrides": {}}
        payload["monthly_decisions"][key] = decision
        if approve:
            treatment_slot = f"{day}:{rule['period']}"
            # An explicit approval replaces this occurrence's prior date override, after review.
            decision["previous_overrides"][treatment_slot] = deepcopy(
                payload["overrides"].get(treatment_slot)
            )
            treatment = deepcopy(rule["routine"])
            treatment["recovery_for"] = key
            payload["overrides"][treatment_slot] = treatment
            for offset in range(-rule.get("recovery_before", 0), rule.get("recovery_after", 0) + 1):
                if offset == 0:
                    continue
                target = day + timedelta(days=offset)
                for period in PERIODS:
                    slot = f"{target}:{period}"
                    current = self.routine(target, period, payload)
                    if current["steps"]:
                        decision["previous_overrides"][slot] = deepcopy(
                            payload["overrides"].get(slot)
                        )
                        recovery = self._recovery_routine(current)
                        recovery["recovery_for"] = key
                        payload["overrides"][slot] = recovery
        return payload, version

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
        period = canonical_period(period)
        with self.db.sessions() as session:
            return {
                c.step_id: c
                for c in session.scalars(
                    select(Completion).where(
                        Completion.day == day,
                        Completion.period.in_(NIGHT_ALIASES if period == "Night" else (period,)),
                    )
                )
            }

    def mark(self, day: date, period: str, step: dict, done: bool) -> None:
        period = canonical_period(period)
        with self.db.sessions.begin() as session:
            existing = session.scalar(
                select(Completion).where(
                    Completion.day == day,
                    Completion.period.in_(NIGHT_ALIASES if period == "Night" else (period,)),
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
                session.execute(
                    delete(Completion).where(
                        Completion.day == day,
                        Completion.step_id == step["id"],
                        Completion.period.in_(NIGHT_ALIASES if period == "Night" else (period,)),
                    )
                )

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
        start_period = canonical_period(start_period)
        payload, _version = self.snapshot()
        monthly_prefixes = tuple(f"{rule['id']}:" for rule in payload["monthly"])
        with self.db.sessions() as session:
            ids = {
                p.id
                for p in session.scalars(select(Product).where(Product.deleted.is_(False)))
                if p.status in ("Active", "Testing")
                and (p.category == "Mask" or IRRITANTS.intersection(p.safety_tags))
            }
        for offset in range(62):
            day = start + timedelta(days=offset)
            for period in PERIODS:
                if offset == 0 and PERIODS.index(period) < PERIODS.index(start_period):
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

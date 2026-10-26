"""Versioned schedule data conversions. Keep v1 stable for migration 0003 and old revisions."""

from copy import deepcopy
from datetime import date

NIGHT_ALIASES = ("Midday", "Evening", "PM", "Night")


def _empty() -> dict:
    return {"shower": False, "steps": []}


def _merge(routines: list[dict]) -> dict:
    """Preserve step identity/order and shower flags when old sessions share one new slot."""
    result = _empty()
    positions = {}
    contributors = []
    for routine in routines:
        if routine.get("steps") or routine.get("recovery_for"):
            contributors.append(routine)
        result.update(
            {
                key: deepcopy(value)
                for key, value in routine.items()
                if key not in ("steps", "shower", "recovery_for")
            }
        )
        result["shower"] |= routine.get("shower", False)
        for step in routine.get("steps", []):
            step = deepcopy(step)
            instructions = step.get("instructions", "")
            step["instructions"] = instructions.replace(
                "Review sun protection for midday use.",
                "Follow product directions and review sun protection.",
            )
            if step["id"] in positions:
                result["steps"][positions[step["id"]]] = step
            else:
                positions[step["id"]] = len(result["steps"])
                result["steps"].append(step)
    if len(contributors) > 1:
        result["session_merge_review"] = True
        result["name"] = "Combined night routine — review step order"
    owners = {r.get("recovery_for") for r in contributors}
    if len(owners) == 1 and None not in owners:
        result["recovery_for"] = owners.pop()
    return result


def _old_routine(source: dict, day: date, period: str, area: str) -> dict:
    overrides, weekly = ("scalp_overrides", "scalp") if area == "Scalp" else ("overrides", "weekly")
    override = source.get(overrides, {}).get(f"{day}:{period}")
    if override is not None:
        return deepcopy(override)
    result = deepcopy(source.get(weekly, {}).get(f"{day.weekday()}:{period}", _empty()))
    for rule in source.get("monthly", []) if area == "Face" else []:
        if not (
            rule["enabled"]
            and rule["weekday"] == day.weekday()
            and rule["ordinal"] == (day.day - 1) // 7 + 1
            and rule["period"] == period
        ):
            continue
        decision = source.get("monthly_decisions", {}).get(f"{rule['id']}:{day}", {}).get("status")
        if rule.get("requires_review") and decision != "approved":
            if decision != "skipped":
                result["steps"].append(
                    {
                        "id": f"{rule['id']}:review",
                        "label": f"REVIEW / OPTIONAL: {rule['name']}",
                        "product_id": None,
                        "optional": False,
                        "review": True,
                    }
                )
            continue
        if rule.get("mode") == "replace":
            result = _empty()
        for step in deepcopy(rule["routine"]["steps"]):
            step["id"] = f"{rule['id']}:{step['id']}"
            result["steps"].append(step)
        result["shower"] |= rule["routine"]["shower"]
    return result


def _night(source: dict, day: date, area: str) -> dict:
    return _merge([_old_routine(source, day, period, area) for period in NIGHT_ALIASES])


def collapse_sessions_v1(payload: dict) -> dict:
    """Convert active plans/templates; historical completion rows and revisions stay untouched."""
    if payload.get("session_format") == 2:
        return deepcopy(payload)
    source = deepcopy(payload)
    source.setdefault("monthly_decisions", {})
    result = deepcopy(source)
    for group in ("weekly", "scalp"):
        values = source.get(group, {})
        result[group] = {}
        for weekday in range(7):
            result[group][f"{weekday}:AM"] = deepcopy(values.get(f"{weekday}:AM", _empty()))
            result[group][f"{weekday}:Night"] = _merge(
                [values.get(f"{weekday}:{period}", _empty()) for period in NIGHT_ALIASES]
            )
    for group, area in (("overrides", "Face"), ("scalp_overrides", "Scalp")):
        values = source.get(group, {})
        result[group] = {
            key: deepcopy(value) for key, value in values.items() if key.endswith(":AM")
        }
        # Resolve all old sessions first, so an override never hides an unedited sibling session.
        days = {key.rsplit(":", 1)[0] for key in values if not key.endswith(":AM")}
        for day in days:
            result[group][f"{day}:Night"] = _night(source, date.fromisoformat(day), area)
    result["monthly"] = deepcopy(source.get("monthly", []))
    for rule in result["monthly"]:
        original_period = rule["period"]
        if rule["period"] in NIGHT_ALIASES:
            rule["period"] = "Night"
            if rule.get("mode") == "replace":
                original = source.get("weekly", {}).get(
                    f"{rule['weekday']}:{original_period}", _empty()
                )
                rule["replace_step_ids"] = [step["id"] for step in original["steps"]]
    for key, decision in result["monthly_decisions"].items():
        previous = decision.get("previous_overrides", {})
        restored = deepcopy(source)
        restored["overrides"] = deepcopy(source.get("overrides", {}))
        restored["monthly_decisions"][key]["status"] = "skipped"
        converted = {
            slot: deepcopy(value) for slot, value in previous.items() if slot.endswith(":AM")
        }
        for slot, routine in previous.items():
            if routine is None:
                restored["overrides"].pop(slot, None)
            else:
                restored["overrides"][slot] = deepcopy(routine)
        days = {slot.rsplit(":", 1)[0] for slot in previous if not slot.endswith(":AM")}
        for day in days:
            has_override = any(
                slot.startswith(f"{day}:") and not slot.endswith(":AM")
                for slot in restored["overrides"]
            )
            converted[f"{day}:Night"] = (
                _night(restored, date.fromisoformat(day), "Face") if has_override else None
            )
        decision["previous_overrides"] = converted
    result["session_format"] = 2
    return result

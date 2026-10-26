from datetime import date, timedelta

import pytest

from skinflow.safety.engine import (
    ProductInfo,
    RoutineContext,
    SafetyPolicy,
    SkinState,
    evaluate,
)
from skinflow.safety.service import SafetyService
from skinflow.services import new_step
from skinflow.tracking import ObservationService

DAY = date(2026, 11, 7)


def product(number, *tags, category="Treatment", available=True):
    return ProductInfo(
        number,
        f"Product {number}",
        category,
        {tag: {"source": "user_reported", "note": "Test evidence"} for tag in tags},
        available=available,
    )


def context(day, *products, period="Night", area="Face"):
    return RoutineContext(day, period, area, [new_step(p.label, p.id) for p in products])


def rule_ids(routines, products, states=None, policy=SafetyPolicy(), start=DAY, end=DAY):
    return {
        f.rule_id
        for f in evaluate(routines, {p.id: p for p in products}, states or {}, start, end, policy)
    }


@pytest.mark.parametrize(
    "tags,expected",
    [
        (("retinoid", "retinoid"), "multiple_retinoids"),
        (("retinoid", "strong_acid"), "retinoid_strong_acid"),
        (("physical_exfoliant", "retinoid"), "physical_active"),
        (("physical_exfoliant", "strong_acid"), "physical_active"),
        (("strong_acid", "peel_off"), "acid_peel_off"),
        (("physical_exfoliant", "peel_off"), "scrub_peel_off"),
        (("detox", "retinoid"), "detox_active"),
    ],
)
def test_interaction_rules(tags, expected):
    products = [product(i, tag) for i, tag in enumerate(tags, 1)]
    routines = [context(DAY, *products)]
    findings = evaluate(routines, {p.id: p for p in products}, {}, DAY, DAY)
    finding = next(f for f in findings if f.rule_id == expected)
    assert finding.days == (DAY,) and len(finding.step_ids) == 2
    assert finding.explanation and finding.alternative and finding.evidence
    assert all("user_reported" in evidence for evidence in finding.product_evidence)


def test_hydration_and_retinoid_are_not_universally_prohibited():
    products = [product(1, "retinoid"), product(2, category="Moisturizer")]
    ids = rule_ids([context(DAY, *products)], products)
    assert ids == {"unverified_ingredients"}


@pytest.mark.parametrize(
    "condition", ["Dry", "Red/Irritated", "Stinging/Burning", "Active Acne", "Recovering"]
)
def test_irritation_respects_affected_region(condition):
    retinol = product(1, "retinoid")
    states = {DAY: [SkinState(DAY, "Eyebrows", condition, 2)]}
    assert "irritated_area" in rule_ids([context(DAY, retinol)], [retinol], states)
    assert "irritated_area" not in rule_ids(
        [context(DAY, retinol, area="Scalp")], [retinol], states
    )


@pytest.mark.parametrize(
    "left_period,right_period,gap,triggered",
    [
        ("Night", "AM", 35, True),
        ("Night", "Night", 48, False),
        ("AM", "Night", 61, False),
    ],
)
def test_spacing_boundary_is_a_personal_preference(left_period, right_period, gap, triggered):
    products = [product(1, "retinoid"), product(2, "strong_acid")]
    first = context(DAY, products[0], period=left_period)
    second = context(DAY + timedelta(days=2), products[1], period=right_period)
    assert (second.timestamp - first.timestamp).total_seconds() / 3600 == gap
    assert ("active_spacing" in rule_ids([first, second], products)) is triggered


def test_sunscreen_placeholder_and_spf15_do_not_satisfy_confirmed_protection():
    retinol = product(1, "retinoid")
    moisturizer = product(2, category="Moisturizer")
    morning = context(DAY, moisturizer, period="AM")
    morning.steps.append(new_step("Unconfirmed SPF30 reminder"))
    night = context(DAY, retinol)
    assert "missing_sunscreen" in rule_ids([morning, night], [retinol, moisturizer])
    sunscreen = product(3, "spf30", category="Sunscreen")
    morning.steps.append(new_step(sunscreen.label, sunscreen.id))
    assert "missing_sunscreen" not in rule_ids([morning, night], [retinol, moisturizer, sunscreen])


@pytest.mark.parametrize("days_after,expected", [(7, True), (8, False)])
def test_aha_sun_protection_window(days_after, expected):
    acid = product(1, "aha")
    past = context(DAY - timedelta(days=days_after), acid)
    morning = context(DAY, period="AM")
    assert ("missing_sunscreen" in rule_ids([past, morning], [acid])) is expected


def test_exfoliation_frequency_and_configurable_limit():
    scrub = product(1, "physical_exfoliant")
    routines = [context(DAY - timedelta(days=2), scrub), context(DAY, scrub)]
    assert "frequent_exfoliation" in rule_ids(routines, [scrub])
    assert "frequent_exfoliation" not in rule_ids(
        routines, [scrub], policy=SafetyPolicy(max_exfoliation_sessions=2)
    )
    assert "frequent_exfoliation" not in rule_ids(
        [context(DAY - timedelta(days=7), scrub), routines[1]], [scrub]
    )


def test_patch_order_and_dry_skin_instruction():
    essence = product(1)
    patch = product(2, "hydrocolloid", "dry_skin", category="Targeted")
    assert "patch_order" in rule_ids([context(DAY, essence, patch)], [essence, patch])
    ids = rule_ids([context(DAY, patch, essence)], [essence, patch])
    assert "patch_order" not in ids and "dry_skin_application" in ids


def test_only_one_mask_and_sunscreen_last():
    masks = [product(1, category="Mask"), product(2, category="Mask")]
    assert "multiple_masks" in rule_ids([context(DAY, *masks)], masks)
    sunscreen = product(3, "spf30", category="Sunscreen")
    assert "sunscreen_order" in rule_ids([context(DAY, sunscreen, masks[0])], [sunscreen, masks[0]])


def test_paused_products_are_excluded_from_possible_exposures():
    products = [product(1, "retinoid"), product(2, "retinoid", available=False)]
    assert "multiple_retinoids" not in rule_ids([context(DAY, *products)], products)


def test_unverified_lists_do_not_generate_guessed_tags(inventory, db):
    unknown = inventory.save(
        {"name": "Unknown serum", "category": "Treatment", "actives": "retinol?"}
    )
    assert unknown.safety_tags == {}
    findings = SafetyService(db).review(DAY)
    assert any(f.rule_id == "unverified_ingredients" for f in findings)


def test_observations_feed_the_read_only_review_without_changing_the_schedule(db, schedule):
    day = date(2026, 10, 27)
    before = schedule.snapshot()
    ObservationService(db).save(
        {"day": day, "region": "Eyebrows", "condition": "Stinging/Burning", "severity": 2}
    )
    findings = SafetyService(db).review(day)
    assert any(f.rule_id == "irritated_area" and f.regions == ("Eyebrows",) for f in findings)
    assert schedule.snapshot() == before


def test_completed_actives_removed_from_plan_still_affect_review(db, schedule):
    day = date(2026, 10, 27)
    step = schedule.routine(day, "Night")["steps"][1]
    schedule.mark(day, "Night", step, True)
    schedule.set_routine(day, "Night", {"shower": False, "steps": []}, weekly=False)
    assert any(
        f.rule_id == "missing_sunscreen" for f in SafetyService(db).review(day + timedelta(days=1))
    )


def test_completed_retinoid_is_checked_against_replacement_in_same_session(db, schedule, inventory):
    day = date(2026, 10, 27)
    pads = schedule.routine(day, "Night")["steps"][1]
    schedule.mark(day, "Night", pads, True)
    inventory.save({"status": "Paused"}, pads["product_id"])
    other = inventory.list(search="Resurfacing Retinol")[0]
    schedule.set_routine(
        day, "Night", {"shower": False, "steps": [new_step(other.label, other.id)]}, weekly=False
    )
    findings = SafetyService(db).review(day)
    assert any(f.rule_id == "multiple_retinoids" for f in findings)


def test_completed_steps_do_not_double_count_planned_sessions(db, schedule):
    day = date(2026, 10, 27)
    pads = schedule.routine(day, "Night")["steps"][1]
    schedule.mark(day, "Night", pads, True)
    findings = SafetyService(db).review(day)
    assert not any(f.rule_id == "multiple_retinoids" for f in findings)

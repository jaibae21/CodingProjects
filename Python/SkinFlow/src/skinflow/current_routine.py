"""The user's October 25, 2026 configuration, persisted once by the seed service."""

from copy import deepcopy

from sqlalchemy import select

from skinflow.database import Database
from skinflow.models import Plan, PlanRevision, Product, RoutineTemplate, Setting
from skinflow.services import PERIODS, empty_routine, new_step, normalize_plan

CONFIG_KEY = "current_routine_2026_10_25"
TAG_SEEDS = {
    "Deep Collagen Daily Nourishing Pads": ("retinoid",),
    "Resurfacing Retinol Serum": ("retinoid", "dry_skin"),
    "Deep Collagen Retinol Power Boosting Capsule Cream": ("retinoid", "spicules", "dry_skin"),
    "AHA 30% / BHA 2% Peeling Serum": ("strong_acid", "aha"),
    "Extra Gentle Daily Scrub": ("physical_exfoliant",),
    "Charcoal Peel-Off Mask": ("peel_off",),
    "Peel Off Pack EX": ("peel_off",),
    "Charcoal Nose Pore Strips": ("peel_off",),
    "Super Green Detox Mask": ("detox",),
    "Pimple Patches": ("hydrocolloid", "dry_skin"),
}
PRODUCT_GUIDANCE = {
    "Extra Gentle Daily Scrub": (
        "Optional; no more than about once weekly if tolerated",
        "Pause during dryness or irritation. Do not combine with retinoids, "
        "strong acids, or peel-off treatments.",
    ),
    "Super Green Detox Mask": (
        "Optional; about every 2–4 weeks, replacing Saturday's mask",
        "Avoid irritated or very dry skin. Do not combine with retinoids, "
        "acids, scrubs, or peel-off masks.",
    ),
    "Charcoal Peel-Off Mask": (
        "Rare / optional, instead of the normal Saturday mask",
        "Avoid eyebrows, hairline, active pimples, irritated, broken or peeling skin, "
        "and nearby exfoliation.",
    ),
    "Peel Off Pack EX": (
        "Rare / optional, instead of the normal Saturday mask",
        "Avoid eyebrows, hairline, active pimples, irritated, broken or peeling skin, "
        "and nearby exfoliation.",
    ),
    "Charcoal Nose Pore Strips": (
        "As needed, infrequently",
        "Avoid irritated skin and other exfoliating treatments in the same session.",
    ),
    "Pimple Patches": (
        "As needed",
        "Cleanse and dry the spot. Apply the patch directly, then skincare around it. "
        "Avoid essence, moisturizer, retinoids, or acids underneath.",
    ),
    "Root-Biome Caffeine Scalp Ampoule": (
        "Tuesday and Thursday shower nights",
        "Shampoo, condition and rinse, then apply to clean scalp according to "
        "packaging and gently massage.",
    ),
}


def build_current(products: list[Product]) -> dict:
    by_name = {product.name: product for product in products}

    def step(name: str, *, substitutes: tuple[str, ...] = (), notes: str = "", area="Face"):
        product = by_name.get(name)
        result = new_step(
            product.label if product else f"{name} — select matching inventory product",
            product.id if product else None,
        )
        result.update(
            region=area,
            instructions=notes,
            skip_conditions="Skip if this product stings or irritates the affected area.",
            substitutions=[by_name[n].id for n in substitutes if n in by_name],
        )
        return result

    gentle = "Gentle Skin Cleanser"
    foam = "Hydrating Cream-to-Foam Cleanser"
    mugwort = "Mugwort Essence"
    cerave = "PM Facial Moisturizing Lotion"
    purito = "Oat-in Calming Gel Cream"
    klairs = "Midnight Blue Calming Cream"

    def routine(names: list[str], **kwargs) -> dict:
        return {"shower": False, "steps": [step(name) for name in names], **kwargs}

    weekly = {f"{day}:{period}": empty_routine() for day in range(7) for period in PERIODS}
    scalp = {f"{day}:{period}": empty_routine() for day in range(7) for period in PERIODS}
    for day in range(7):
        weekly[f"{day}:AM"] = routine([gentle, mugwort])
        weekly[f"{day}:AM"]["steps"].append(
            new_step(
                "Broad-spectrum SPF 30+ — product unconfirmed; SPF 15 is not equivalent",
                review=True,
            )
        )
    for day in (0, 4):
        weekly[f"{day}:Night"] = routine([foam, mugwort, cerave], name="Recovery")
    for day in (1, 3):
        weekly[f"{day}:Night"] = routine(
            [gentle, "Deep Collagen Daily Nourishing Pads", mugwort, cerave],
            shower=True,
            name="Nourishing Pads",
        )
        pads = weekly[f"{day}:Night"]["steps"][1]
        pads["skip_conditions"] = (
            "Skip on red, peeling, stinging, dry or inflamed areas, including eyebrows."
        )
        pads["instructions"] = "Do not combine with a scrub or another retinoid. Follow the label."
        scalp[f"{day}:Night"] = {
            "name": "Shower and scalp",
            "shower": True,
            "steps": [
                new_step("Shampoo"),
                new_step("Condition and rinse"),
                step(
                    "Root-Biome Caffeine Scalp Ampoule",
                    area="Scalp",
                    notes="Apply after shampooing; follow packaging. Gently massage.",
                ),
            ],
        }
        for scalp_step in scalp[f"{day}:Night"]["steps"]:
            scalp_step["region"] = "Scalp"
    weekly["2:Night"] = routine(
        ["Super Aqua Ultra Hyalron Cleansing Foam", mugwort, purito], name="Lightweight recovery"
    )
    weekly["2:Night"]["steps"][0] = step(
        "Super Aqua Ultra Hyalron Cleansing Foam", substitutes=(foam,)
    )
    weekly["5:Night"] = {
        "name": "One mask session",
        "shower": False,
        "steps": [
            step(gentle),
            step(
                "White Rice Essence Mask",
                substitutes=("Real Oatmeal Essence Mask", "Milk One Pack Coffee Milk Mask"),
                notes="Use only one mask. Follow its application time.",
            ),
            step(klairs, substitutes=(cerave,)),
        ],
    }
    weekly["6:Night"] = routine(
        [gentle, mugwort, "Deep Collagen Retinol Power Boosting Capsule Cream", cerave],
        name="Retinol treatment",
    )
    weekly["6:Night"]["steps"][2]["instructions"] = (
        "Apply to dry skin according to packaging. Replaces CeraVe retinol; do not combine. "
        "User reports spicules. Follow product directions and review sun protection."
    )
    monthly = [
        {
            "id": "monthly-aha-review",
            "name": "Optional AHA/BHA — review before use",
            "ordinal": 1,
            "weekday": 5,
            "period": "Night",
            "enabled": True,
            "requires_review": True,
            "mode": "replace",
            "recovery_before": 2,
            "recovery_after": 2,
            "routine": routine([gentle, "AHA 30% / BHA 2% Peeling Serum", klairs]),
        }
    ]
    monthly[0]["routine"]["steps"][1]["instructions"] = (
        "High-strength acid. Follow specific application and removal instructions. "
        "Skip when skin is uncomfortable. Review surrounding recovery days."
    )
    return {
        "session_format": 2,
        "weekly": weekly,
        "monthly": monthly,
        "overrides": {},
        "scalp": scalp,
        "scalp_overrides": {},
        "monthly_decisions": {},
    }


def initialize_current(database: Database) -> None:
    """One-time upgrade of the user's requested configuration, preserving previous plans."""
    with database.sessions.begin() as session:
        if session.get(Setting, CONFIG_KEY):
            return
        products = list(session.scalars(select(Product).order_by(Product.id)))
        for product in products:
            if product.name in PRODUCT_GUIDANCE:
                frequency, instructions = PRODUCT_GUIDANCE[product.name]
                if not product.frequency:
                    product.frequency = frequency
                if not product.instructions:
                    product.instructions = instructions
            if product.name in TAG_SEEDS and not product.safety_tags:
                product.safety_tags = {
                    tag: {
                        "source": "user_reported",
                        "note": "User-supplied product name / routine. Verify packaging.",
                    }
                    for tag in TAG_SEEDS[product.name]
                }
        plan = session.get(Plan, 1)
        if plan is None:
            raise ValueError("Initialize the original baseline before the current routine.")
        first = session.scalar(select(PlanRevision).order_by(PlanRevision.id))
        session.add(
            RoutineTemplate(name="Original baseline", payload=normalize_plan(first.payload))
        )
        session.add(
            RoutineTemplate(
                name="Saved plan before current routine", payload=deepcopy(plan.payload)
            )
        )
        current = build_current(products)
        session.add(
            RoutineTemplate(name="Current routine — October 25, 2026", payload=deepcopy(current))
        )
        plan.payload = current
        plan.version += 1
        session.add(
            PlanRevision(
                description="Current routine supplied October 25, 2026", payload=deepcopy(current)
            )
        )
        session.add(Setting(key=CONFIG_KEY, value="1"))

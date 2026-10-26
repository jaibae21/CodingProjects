"""User-supplied inventory only; no inferred ingredient lists or concentrations."""

from copy import deepcopy

from skinflow.database import Database
from skinflow.models import Plan, PlanRevision, Product, Setting
from skinflow.services import new_step

# Active descriptions below are explicitly present in the brief or product name.
PRODUCTS = [
    ("Cetaphil", "Gentle Skin Cleanser", "Cleanser", ""),
    ("CeraVe", "Hydrating Cream-to-Foam Cleanser", "Cleanser", ""),
    ("Cetaphil", "Extra Gentle Daily Scrub", "Cleanser", ""),
    ("Avène", "Cleanance Cleansing Gel", "Cleanser", ""),
    ("MISSHA", "Super Aqua Ultra Hyalron Cleansing Foam", "Cleanser", ""),
    ("", "Deep Collagen Daily Nourishing Pads", "Treatment", "Retinol (user supplied; unverified)"),
    ("CeraVe", "Resurfacing Retinol Serum", "Treatment", "Retinol (name; unverified)"),
    (
        "Sungboon Editor",
        "Deep Collagen Retinol Power Boosting Capsule Cream",
        "Treatment",
        "Retinol (name; unverified)",
    ),
    (
        "Cos De BAHA",
        "AHA 30% / BHA 2% Peeling Serum",
        "Treatment",
        "AHA 30% / BHA 2% (user-supplied name; unverified)",
    ),
    ("I'm From", "Mugwort Essence", "Treatment", ""),
    ("CeraVe", "PM Facial Moisturizing Lotion", "Moisturizer", ""),
    ("Cetaphil", "Daily Facial Moisturizer SPF 15", "Moisturizer", ""),
    ("Klairs", "Midnight Blue Calming Cream", "Moisturizer", ""),
    ("PURITO SEOUL", "Oat-in Calming Gel Cream", "Moisturizer", ""),
    ("Pureal", "White Rice Essence Mask", "Mask", ""),
    ("Farmstay", "Real Oatmeal Essence Mask", "Mask", ""),
    ("A'PIEU", "Milk One Pack Coffee Milk Mask", "Mask", ""),
    ("", "Super Green Detox Mask", "Mask", ""),
    ("", "Charcoal Peel-Off Mask", "Mask", ""),
    ("Tsururi", "Peel Off Pack EX", "Mask", ""),
    ("Hero", "Pimple Patches", "Targeted", ""),
    ("CeraVe", "Pimple Patches", "Targeted", ""),
    ("", "Charcoal Nose Pore Strips", "Targeted", ""),
    ("NINE LESS", "Root-Biome Caffeine Scalp Ampoule", "Scalp", ""),
]


def _seed_baseline(database: Database) -> None:
    """Seed once, atomically. Never repopulate products a user deleted."""
    with database.sessions.begin() as session:
        if session.get(Setting, "seed_version"):
            return
        products = []
        for brand, name, category, actives in PRODUCTS:
            product = Product(
                brand=brand,
                name=name,
                category=category,
                actives=actives,
                notes="From initial inventory. Verify label and usage instructions.",
            )
            session.add(product)
            products.append(product)
        session.flush()

        def step(index: int, *, optional: bool = False, suffix: str = "") -> dict:
            product = products[index]
            return new_step(product.label + suffix, product.id, optional=optional)

        weekly = {}
        for weekday in range(7):
            weekly[f"{weekday}:AM"] = {
                "shower": False,
                "steps": [
                    step(0),
                    step(9, optional=True, suffix=" — if tolerated"),
                    new_step(
                        "Broad-spectrum SPF 30+ — sunscreen product not yet confirmed", review=True
                    ),
                ],
            }
            night_steps = [step(0)]
            if weekday in (0, 2, 4):
                night_steps = [step(1), step(9, optional=True, suffix=" — if tolerated")]
            elif weekday in (1, 3):
                night_steps.append(step(5, optional=True, suffix=" — if tolerated"))
            elif weekday == 5:
                night_steps.append(
                    new_step(
                        "Hydrating mask — choose a tolerated product when scheduled", optional=True
                    )
                )
            else:
                night_steps.append(
                    step(6, optional=True, suffix=" — one retinol only, if skin is comfortable")
                )
            night_steps.append(step(10, suffix=" — or PURITO Oat-in Calming Gel Cream"))
            weekly[f"{weekday}:PM"] = {"shower": weekday in (1, 3), "steps": night_steps}

        # This is an informational review reminder, not a scheduled application of a peel.
        monthly = [
            {
                "id": "historical-peel-review",
                "name": "Historical strong peel review",
                "ordinal": 1,
                "weekday": 5,
                "period": "PM",
                "enabled": True,
                "routine": {
                    "shower": False,
                    "steps": [
                        new_step(
                            "CAUTION / REVIEW: historical AHA 30% / BHA 2% peel; do not treat this "
                            "reminder as an instruction to apply. "
                            "Review use and surrounding recovery days.",
                            review=True,
                        )
                    ],
                },
            }
        ]
        payload = {"weekly": weekly, "monthly": monthly, "overrides": {}}
        session.add(Plan(id=1, version=1, payload=payload))
        session.add(
            PlanRevision(description="Initial editable baseline", payload=deepcopy(payload))
        )
        session.add(Setting(key="seed_version", value="1"))


def seed(database: Database) -> None:
    from skinflow.current_routine import initialize_current

    _seed_baseline(database)
    initialize_current(database)

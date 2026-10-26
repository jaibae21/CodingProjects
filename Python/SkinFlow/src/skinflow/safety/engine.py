"""Pure, deterministic caution rules. Findings never mutate a routine or diagnose skin."""

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from itertools import combinations

from skinflow.safety.tags import IRRITANTS

PERIOD_HOURS = {"AM": 8, "Night": 21}
AAD_EXFOLIATION = (
    "https://www.aad.org/public/everyday-care/skin-care-secrets/routine/safely-exfoliate-at-home"
)
AAD_RETINOIDS = "https://www.aad.org/public/diseases/acne/derm-treat/treat"
FDA_AHA = "https://www.fda.gov/cosmetics/cosmetic-ingredients/alpha-hydroxy-acids"


@dataclass(frozen=True)
class ProductInfo:
    id: int
    label: str
    category: str
    tags: dict
    available: bool = True
    ingredients_verified: bool = False


@dataclass(frozen=True)
class RoutineContext:
    day: date
    period: str
    area: str
    steps: list[dict]
    actual: bool = False

    @property
    def timestamp(self) -> datetime:
        return datetime.combine(self.day, time(PERIOD_HOURS[self.period]))


@dataclass(frozen=True)
class SkinState:
    day: date
    region: str
    condition: str
    severity: int


@dataclass(frozen=True)
class SafetyPolicy:
    active_gap_hours: int = 48
    max_exfoliation_sessions: int = 1

    def __post_init__(self):
        if not 0 <= self.active_gap_hours <= 168:
            raise ValueError("Active spacing must be between 0 and 168 hours.")
        if not 1 <= self.max_exfoliation_sessions <= 14:
            raise ValueError("Exfoliation limit must be between 1 and 14 sessions per 7 days.")


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    evidence: str
    explanation: str
    alternative: str
    days: tuple[date, ...]
    step_ids: tuple[str, ...]
    regions: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()
    product_evidence: tuple[str, ...] = ()
    sessions: tuple[str, ...] = ()

    def text(self) -> str:
        dates = ", ".join(self.sessions) or ", ".join(day.isoformat() for day in self.days)
        details = (
            f"\nProduct evidence: {'; '.join(self.product_evidence)}"
            if self.product_evidence
            else ""
        )
        return (
            f"{self.severity.upper()} · {self.evidence} · {dates}\n"
            f"{self.explanation}\nConsider: {self.alternative}{details}"
        )


def regions_overlap(region: str, area: str) -> bool:
    facial = {"face", "eyebrows", "forehead", "cheeks", "nose", "chin", "hairline"}
    return region.casefold() == area.casefold() or (
        region.casefold() in facial
        and area.casefold() in facial
        and (region.casefold() == "face" or area.casefold() == "face")
    )


def evaluate(
    routines: list[RoutineContext],
    products: dict[int, ProductInfo],
    states: dict[date, list[SkinState]],
    start: date,
    end: date,
    policy: SafetyPolicy = SafetyPolicy(),
) -> list[Finding]:
    """Assess exposures; optional steps count as possible use, not completed use."""
    findings: list[Finding] = []
    exposures: list[tuple[RoutineContext, list[tuple[dict, ProductInfo]]]] = []

    def add(
        rule, severity, evidence, explanation, alternative, contexts, steps, sources=(), regions=()
    ):
        product_notes = set()
        for step in steps:
            product = products.get(step.get("product_id"))
            if product:
                for tag, value in product.tags.items():
                    product_notes.add(f"{product.label}: {tag} ({value['source']})")
        findings.append(
            Finding(
                rule,
                severity,
                evidence,
                explanation,
                alternative,
                tuple(sorted({r.day for r in contexts})),
                tuple(dict.fromkeys(s["id"] for s in steps)),
                tuple(regions),
                tuple(sources),
                tuple(sorted(product_notes)),
                tuple(dict.fromkeys(f"{r.day} {r.period} ({r.area})" for r in contexts)),
            )
        )

    for routine in sorted(
        routines, key=lambda r: (r.day, PERIOD_HOURS[r.period], r.area, r.actual)
    ):
        pairs = [
            (s, products[s["product_id"]])
            for s in routine.steps
            if s.get("product_id") in products
            and (products[s["product_id"]].available or routine.actual or s.get("_completed"))
        ]
        exposures.append((routine, pairs))
        if not start <= routine.day <= end or routine.actual:
            continue

        def tagged(tag):
            return [(s, p) for s, p in pairs if tag in p.tags]

        retinoids, acids = tagged("retinoid"), tagged("strong_acid")
        physical, peel = tagged("physical_exfoliant"), tagged("peel_off")
        combos = [
            (
                "multiple_retinoids",
                len(retinoids) > 1,
                retinoids,
                "Multiple retinoid steps are planned or logged in the same session.",
                "Use one retinoid product.",
                "Conservative preference",
            ),
            (
                "retinoid_strong_acid",
                bool(retinoids and acids),
                retinoids + acids,
                "A retinoid and strong acid overlap in planned/logged use; irritation may add up.",
                "Separate these treatments and consider a recovery session.",
                "Conservative preference",
            ),
            (
                "physical_active",
                bool(physical and (retinoids or acids)),
                physical + retinoids + acids,
                "A scrub overlaps a retinoid or strong acid; irritation may increase.",
                "Leave out the scrub and review the active treatment.",
                "Established concern",
            ),
            (
                "acid_peel_off",
                bool(acids and peel),
                acids + peel,
                "Strong acid and peel-off treatment overlap in planned/logged use.",
                "Choose a recovery routine instead of stacking exfoliating treatments.",
                "Conservative preference",
            ),
            (
                "scrub_peel_off",
                bool(physical and peel),
                physical + peel,
                "A scrub and peel-off treatment are planned together.",
                "Choose a single treatment and avoid irritated areas.",
                "Conservative preference",
            ),
            (
                "detox_active",
                bool(tagged("detox") and (retinoids or acids or physical or peel)),
                tagged("detox") + retinoids + acids + physical + peel,
                "The detox mask overlaps another potentially irritating treatment.",
                "Use the mask as a substitution on another day, following its label.",
                "Conservative preference",
            ),
            (
                "multiple_masks",
                sum(p.category == "Mask" for _s, p in pairs) > 1,
                [(s, p) for s, p in pairs if p.category == "Mask"],
                "More than one mask is planned in this session.",
                "Choose one mask and use substitutions to replace it.",
                "Conservative preference",
            ),
        ]
        for rule, triggered, involved, explanation, alternative, evidence in combos:
            if triggered:
                add(
                    rule,
                    "warning",
                    evidence,
                    explanation,
                    alternative,
                    [routine],
                    [s for s, _p in involved],
                    (AAD_EXFOLIATION,),
                )
        if acids:
            add(
                "strong_acid_review",
                "high",
                "Established concern",
                "A high-strength acid is planned. Verify directions and skin condition.",
                "Skip it when skin is uncomfortable; review surrounding recovery days.",
                [routine],
                [s for s, _p in acids],
                (FDA_AHA,),
            )
        irritants = [(s, p) for s, p in pairs if IRRITANTS.intersection(p.tags)]
        affected = [
            state
            for state in states.get(routine.day, [])
            if state.condition
            in ("Dry", "Red/Irritated", "Stinging/Burning", "Active Acne", "Recovering")
            and any(
                regions_overlap(state.region, s.get("region", routine.area)) for s, _p in irritants
            )
        ]
        if affected and irritants:
            add(
                "irritated_area",
                "high",
                "Established concern",
                "Potential irritants overlap a reported uncomfortable or recovering area. "
                "Stinging is not something you need to push through.",
                "Avoid these treatments on the affected area and review a recovery override.",
                [routine],
                [s for s, _p in irritants],
                (AAD_EXFOLIATION, AAD_RETINOIDS),
                sorted({state.region for state in affected}),
            )
        dry_steps = [s for s, p in pairs if "dry_skin" in p.tags]
        if dry_steps:
            add(
                "dry_skin_application",
                "info",
                "Product instruction / user report",
                "These steps require dry skin according to the recorded instructions.",
                "Allow skin to dry first; follow the individual product directions.",
                [routine],
                dry_steps,
            )
        ordered_pairs = [(s, p) for s, p in pairs if not s.get("_completed")]
        for index, (step, product) in enumerate(ordered_pairs):
            earlier = ordered_pairs[:index]
            if "hydrocolloid" in product.tags and any(
                p.category in ("Treatment", "Moisturizer") for _s, p in earlier
            ):
                add(
                    "patch_order",
                    "warning",
                    "Product instruction / user report",
                    "A hydrocolloid patch follows essence, treatment, or moisturizer.",
                    "Apply the patch to cleansed, dry skin; apply other skincare around it.",
                    [routine],
                    [step] + [s for s, _p in earlier],
                )
            if "spf30" in product.tags and index != len(ordered_pairs) - 1:
                add(
                    "sunscreen_order",
                    "info",
                    "Product instruction / user report",
                    "Confirmed sunscreen is followed by another skincare product.",
                    "Make sunscreen the last skincare step, following its label.",
                    [routine],
                    [step],
                )
        unknown = [s for s, p in pairs if not p.ingredients_verified]
        if unknown:
            add(
                "unverified_ingredients",
                "info",
                "Data incomplete",
                "Ingredient lists are unverified; no warning does not establish compatibility.",
                "Verify product labels and update safety tags when information is available.",
                [routine],
                unknown,
            )

    # Pairwise spacing is a configurable personal preference, never a universal medical threshold.
    actives = [
        (r, [(s, p) for s, p in pairs if {"retinoid", "strong_acid"}.intersection(p.tags)])
        for r, pairs in exposures
    ]
    actives = [(r, pairs) for r, pairs in actives if pairs]
    for (left, lp), (right, rp) in combinations(actives, 2):
        hours = (right.timestamp - left.timestamp).total_seconds() / 3600
        if (
            left.area == right.area
            and 0 < hours < policy.active_gap_hours
            and (start <= left.day <= end or start <= right.day <= end)
        ):
            add(
                "active_spacing",
                "warning",
                "Conservative preference",
                f"Active sessions are {hours:g} hours apart, below your "
                f"{policy.active_gap_hours}-hour preference.",
                "Review spacing or choose recovery; follow product/clinician instructions.",
                [left, right],
                [s for s, _p in lp + rp],
            )

    for routine, pairs in exposures:
        if routine.actual or not start <= routine.day <= end or routine.area != "Face":
            continue
        if routine.period == "AM":
            sensitive = [
                (r, s, p)
                for r, entries in exposures
                for s, p in entries
                if r.area == "Face"
                and r.day <= routine.day
                and (
                    ("aha" in p.tags and r.day >= routine.day - timedelta(days=7))
                    or ("retinoid" in p.tags and r.day >= routine.day - timedelta(days=1))
                )
            ]
            # Later same-day actives also call for a sun-protection check that morning.
            if sensitive and not any("spf30" in p.tags for _s, p in pairs):
                add(
                    "missing_sunscreen",
                    "warning",
                    "Established concern",
                    "No confirmed broad-spectrum SPF 30+ product is in this morning's plan near "
                    "a retinoid or AHA treatment. A reminder or SPF 15 cannot confirm protection.",
                    "Confirm appropriate sunscreen and sun protection; follow treatment labels.",
                    [routine],
                    [s for _r, s, _p in sensitive],
                    (FDA_AHA, AAD_RETINOIDS),
                )
        exfoliating = [
            s
            for s, p in pairs
            if {"physical_exfoliant", "strong_acid", "aha", "peel_off"}.intersection(p.tags)
        ]
        if exfoliating:
            window = [
                (r, entries)
                for r, entries in exposures
                if r.area == routine.area
                and routine.day - timedelta(days=6) <= r.day <= routine.day
                and r.timestamp <= routine.timestamp
                and any(
                    {"physical_exfoliant", "strong_acid", "aha", "peel_off"}.intersection(p.tags)
                    for _s, p in entries
                )
            ]
            if len(window) > policy.max_exfoliation_sessions:
                add(
                    "frequent_exfoliation",
                    "warning",
                    "Conservative preference",
                    f"{len(window)} exfoliation sessions fall in 7 days, above your "
                    f"{policy.max_exfoliation_sessions}-session preference.",
                    "Review frequency and recovery days, tolerance, and product directions.",
                    [r for r, _entries in window],
                    exfoliating,
                    (AAD_EXFOLIATION,),
                )
    unique = {(f.rule_id, f.days, f.step_ids, f.regions): f for f in findings}
    ranks = {"high": 0, "warning": 1, "info": 2}
    return sorted(unique.values(), key=lambda f: (ranks[f.severity], f.days, f.rule_id))

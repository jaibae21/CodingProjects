"""Explicit user/label evidence; never infer ingredient lists from product names."""

TAGS = {
    "retinoid": "Retinoid",
    "strong_acid": "Strong exfoliating acid",
    "aha": "AHA exfoliant",
    "physical_exfoliant": "Physical scrub / exfoliant",
    "peel_off": "Peel-off treatment / pore strip",
    "detox": "Detox mask (personal caution)",
    "spicules": "Spicules (user reported)",
    "hydrocolloid": "Hydrocolloid patch",
    "dry_skin": "Requires dry skin before application",
    "spf30": "Confirmed broad-spectrum SPF 30+",
}
EVIDENCE = ("user_reported", "label_verified")
IRRITANTS = {
    "retinoid",
    "strong_acid",
    "aha",
    "physical_exfoliant",
    "peel_off",
    "detox",
    "spicules",
}


def validate_tags(tags: dict) -> None:
    if not isinstance(tags, dict):
        raise ValueError("Safety tags must include an evidence source.")
    for name, evidence in tags.items():
        if name not in TAGS or not isinstance(evidence, dict):
            raise ValueError("Unknown safety tag.")
        if evidence.get("source") not in EVIDENCE or not isinstance(evidence.get("note", ""), str):
            raise ValueError("Each safety tag needs user-reported or label-verified evidence.")

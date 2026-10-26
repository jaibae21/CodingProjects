# Offline safety rules

The engine runs locally without AI or network access. It returns findings and never changes a plan.
The service supplies planned steps, distinct completed products removed from those plans, recorded
product tags, and skin states active on each reviewed date. Observations/photos remain local.

## Evidence and scope

Each tag records `user_reported` or `label_verified` evidence and notes. Seeded tags come only
from the supplied names/configuration. The engine does not parse arbitrary actives text or guess
concentrations. Full ingredient verification is separate. Missing ingredient information produces
an information finding; no warning is not proof of compatibility.

Findings include a stable rule ID, severity, explanation, alternative, affected dates/sessions/steps,
relevant regions, product evidence, and source links where applicable. Broad established concerns
are distinguished from conservative personal choices. Particular products still need individual review.

## Rules

| Rule ID | Trigger / basis |
| --- | --- |
| `multiple_retinoids` | Multiple retinoid steps in one session; conservative preference |
| `retinoid_strong_acid` | Retinoid plus strong acid; conservative additive-irritation caution |
| `physical_active` | Scrub plus retinoid/strong acid; established general irritation concern |
| `acid_peel_off` | Strong acid plus peel-off; conservative preference |
| `scrub_peel_off` | Scrub plus peel-off; conservative preference |
| `detox_active` | Detox mask plus another irritant; supplied personal preference |
| `multiple_masks` | Multiple masks in a session; supplied preference |
| `strong_acid_review` | Recorded strong acid; review directions and skin condition |
| `irritated_area` | Recorded irritant overlaps an uncomfortable/recovering skin state |
| `active_spacing` | Retinoid/strong-acid sessions below configured spacing preference |
| `frequent_exfoliation` | Seven-day exfoliation sessions exceed configured preference |
| `missing_sunscreen` | No tagged SPF 30+ in Morning near retinoid/AHA exposure |
| `dry_skin_application` | Recorded dry-skin application requirement |
| `patch_order` | Patch follows treatment or moisturizer in the planned order |
| `sunscreen_order` | Confirmed sunscreen precedes another skincare product |
| `unverified_ingredients` | Scheduled products lack verified full ingredient lists |

Defaults are 48 hours between active sessions and one exfoliation session per seven days.
They are configurable preferences, not medical limits. Approximate session times are Morning
08:00 and Night 21:00. Actual completion timestamps remain stored, including legacy session records;
spacing estimates use the session time rather than asserting exact use time.

The AHA sun-protection lookback is seven days. The retinoid check uses the same/preceding day;
this is an app heuristic, not a claim that sensitivity ends after one day. A reminder or SPF 15
does not satisfy confirmed SPF 30+ protection. Optional planned steps count as possible exposure.
Inactive products are excluded from planned exposure, but logged actual use remains included.
Distinct completed products are combined with planned session exposures without double-counting steps.

Face-wide applications overlap facial subregions such as eyebrows; scalp routines remain separate.
The latest observation per region applies until resolved or superseded. Historical review ignores
future states. Guidance directs persistent, severe, painful, possibly infected, or otherwise
concerning observations to professional evaluation without diagnosis or causal attribution.

## Primary references

- [AAD: Safely exfoliating at home](https://www.aad.org/public/everyday-care/skin-care-secrets/routine/safely-exfoliate-at-home)
  supports general irritation, retinoid/exfoliation, damaged-skin, and frequency cautions.
- [AAD: Acne treatment](https://www.aad.org/public/diseases/acne/derm-treat/treat)
  discusses retinoid irritation and following clinician instructions, including sun protection.
- [FDA: Alpha hydroxy acids](https://www.fda.gov/cosmetics/cosmetic-ingredients/alpha-hydroxy-acids)
  discusses irritation, sun sensitivity, and the importance of strength/formulation.
- [FDA: AHA labeling guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/guidance-industry-labeling-cosmetics-containing-alpha-hydroxy-acids)
  addresses sun protection during AHA use and the following week.
- [AAD: Rash signs needing attention](https://www.aad.org/public/everyday-care/itchy-skin/rash/rash-101)
  supports referring concerning symptoms for care rather than diagnosing them in the app.

Reviewed October 25, 2026. Broad source guidance does not establish every product-pair rule or
numeric preference; app-specific conservative choices are labelled accordingly.

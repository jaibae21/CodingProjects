# Phase 1
 - Any dropdown like options are hard to see in Light mode but if its in dark mode its fine. I believe this is due to the system theme settings interferring.
 - The Baseline Routine Calendar does not need to have the Broad Spectrum SPF 30+ for the AM. The if tolerated (optional) can be removed from all entries since I do use it. 
  - Need to add current schedule. The baseline is correct but just not what I currently do

## Phase 2 follow-up — October 25, 2026

The original notes above are preserved. Implementation status:

- **Light-mode dropdowns:** explicit application, popup-list, and calendar colours now override
  conflicting system palettes. Automated tests start from a dark palette and verify light popup
  colours. A light-mode popup preview was inspected; please retest on the actual Windows desktop.
- **SPF and optional labels:** the newer current-routine configuration explicitly includes an
  unconfirmed SPF 30+ Morning reminder, so that latest instruction takes precedence over removing
  it. SPF 15 stays distinct. Current product labels omit repeated "if tolerated/optional" text;
  skip conditions and directions preserve the requested precautions.
- **Current schedule:** added Morning/Midday/Evening/Night, Sunday midday Sungboon retinol,
  Saturday mask substitutions, independent Tuesday/Thursday scalp care, monthly occurrence review,
  and approved recovery overrides. Original and previously saved plans remain available as templates.

Validation: 87 unit/GUI tests pass in `.venv`; lint and formatting checks pass. Tests cover the
Phase 1 upgrade, actual completion history, skin states, safety boundaries, and approve/cancel flows.
The packaged executable remains unvalidated; these results cover the source application.

### Suggested manual checks

1. Launch normally and inspect light-mode dropdowns, date popups, product forms, and dark mode.
2. Check Wednesday Night, Saturday Evening, Sunday Midday, and the independent Scalp view.
3. On a first Saturday, review the monthly treatment, cancel, and confirm nothing changes.
4. Approve only when intended, inspect Thursday–Monday, then skip and verify the normal plan returns.
5. Move a Scalp session and confirm the facial pads remain on their original date.
6. Record an eyebrow observation, review affected-product warnings, then resolve the state.
7. Edit a session, restart, and confirm that the new configuration is not reapplied over the edit.

## Correction — Morning and Night only

The user corrected the generated current-routine specification: support Morning and a single
Night session covering evening/nighttime. The earlier four-session follow-up above is historical.

- Midday and Evening selectors are removed. Saturday's mask/monthly treatment and Sunday's
  retinol are Night routines; scalp care remains independent.
- Migration `0003` combines saved legacy sessions without erasing actual completion labels or
  timestamps. Plans, date overrides, monthly recovery ownership, templates, and rollback remain usable.
- Multiple nonempty old sessions are combined in their prior order and marked for order review.
- Validation: 94 tests pass in `.venv`, plus lint and formatting checks. Tests include a real
  upgrade from the four-session schema, empty overrides, monthly replacement scope, restoration,
  completion history, and skipping an approved monthly treatment after conversion.

For manual testing, use Morning/Night wherever the older checklist mentions Evening or Midday.

# SkinFlow implementation plan

## Current status

Phase 1 is implemented on the initial development branch, `feature/skinflow-phase-1`.
The project lives in `Python/SkinFlow`; development and tests use its `.venv`.
The Phase 1 validation run passed 33 unit/GUI tests, lint, formatting, dependency consistency,
and an isolated offscreen startup check. Dashboard and calendar screenshots were inspected.
These are recorded results from that run; rerun relevant checks after code changes.

Later phases below are planned work. The Windows build script exists, but a packaged
executable has not been built or validated. See [README.md](README.md) for launch commands
and [architecture](docs/ARCHITECTURE.md) for module boundaries and persistence decisions.

## Phase 1 — architecture, inventory, and editable calendar

- [x] Create the project directory, development branch, and project virtual environment.
- [x] Configure package metadata, dependencies, local launch, and ignored artifacts.
- [x] Separate PySide6 views, services, database lifecycle, and migrations.
- [x] Define product, plan, revision, completion, and settings models with an initial migration.
- [x] Seed the 24 supplied products once, leaving missing details unknown/unverified.
- [x] Seed the editable AM/PM baseline and first-Saturday caution/review reminder.
- [x] Implement inventory creation, editing, search/filtering, archiving, and deletion.
- [x] Preserve historical routine/completion records after product changes and deletion.
- [x] Implement the weekly calendar, ordered step editor, and shower flags.
- [x] Add monthly ordinal-weekday recurrence, date overrides, and one-off moves.
- [x] Record completion separately from planned activities.
- [x] Maintain schedule revisions, rollback, and stale-editor checks.
- [x] Provide dashboard, navigation, light/dark themes, settings, and database backup.
- [x] Add unit/GUI tests and verify restart persistence and offline functionality.
- [x] Document setup, launch, architecture, agent workflow, and future phases.
- [x] Supply a PyInstaller build script for later packaging validation.

Acceptance: launch from the virtual environment without credentials or network access;
edit inventory and routines; preserve changes after restart; keep actual completion history
independent of plan edits; pass the Phase 1 automated checks.

## Phase 2 — scheduling safety rules and skin tracking

1. Add a migration and observation service for symptom, severity, region, date, notes,
   and optional local photo references.
2. Introduce evidence-aware ingredient tags; retain unknown and unverified information.
3. Build an AI-independent rule engine covering:
   - Multiple retinoids and retinoids combined with strong acids.
   - Physical exfoliation combined with retinoids or strong acids.
   - Strong acids combined with peel-off treatments.
   - Active treatments on reported irritated or damaged areas.
   - Frequent exfoliation and active treatments scheduled too closely together.
   - Missing sunscreen around sun-sensitive treatments.
4. Give each finding a stable rule ID, severity, explanation, affected steps/dates,
   suggested alternatives, and evidence category.
5. Surface findings on the dashboard and recheck surrounding days after schedule edits/moves.
6. Provide explicit recovery-day override assistance around recorded strong-treatment use.
7. Add the observation timeline alongside products actually used. Show temporal
   associations without asserting causation or diagnosing conditions.
8. Add professional-evaluation guidance for concerning symptoms as specified in the brief.

Acceptance: test each safety rule and its boundaries, observation persistence/editing,
missing-data handling, recovery overrides, and conflict review after a move. All work offline.

## Phase 3 — AI assistant with proposal review and approval

1. Verify current official Responses API/SDK documentation, structured-output support,
   approved configurable models, and pricing. Document model costs and context budgets.
2. Add the optional OpenAI dependency and a service for concise context building,
   bounded requests, timeouts, and per-session context with optional local history.
3. Add controls for sharing inventory, ingredients, schedule, actual completions,
   observations, and application rules. Keep credential and photo sharing explicit.
4. Read API credentials from environment variables or the OS credential store.
5. Define a closed proposal schema with valid operations, dates, and product references.
   Give the AI no arbitrary SQL or unrestricted database-write capability.
6. Build a review screen showing the exact changes and deterministic safety findings.
7. Apply approved proposals through services only after explicit user approval and a
   current-plan version check. Reject invalid/stale proposals without changing the schedule.
8. Support offline mode and useful timeout/API-error feedback.

Acceptance: use mocked responses to test answers, schema failures, invalid references,
privacy filters, session context, timeouts, API failures, approval/rejection, and stale plans.
No AI-generated routine change is applied automatically; offline features stay usable.

## Phase 4 — usability, data portability, and Windows distribution

1. Add versioned JSON import/export with validation, duplicate handling, and review.
2. Add guided database restore with a pre-restore backup and validation before replacement.
3. Address image portability, keyboard navigation, notifications, calendar/card scaling,
   and history performance as needed.
4. Verify the PyInstaller bundle includes migrations and launches on a clean Windows machine.
5. Test persisted data across packaged upgrades, backups/restores, and both themes.
6. Refresh dependency snapshots after testing supported versions and review distribution
   contents for credentials, personal data, and generated development files.
7. Produce and document the Windows distribution after packaging checks pass.

Acceptance: automated import/export and restore round-trips, invalid-input rejection,
GUI regressions, clean-machine executable startup, packaged schema upgrades, and a
release checklist documenting the actual verification results.

## Progress maintenance

Keep completed work checked only when it is implemented and verified. Update acceptance
results after relevant checks. Retain explicit boundaries between working functionality,
supplied scaffolding, and planned features. Follow the existing user-authorized phase scope;
this roadmap alone does not initiate implementation of the remaining phases.

# Future Additions
Seasonal routine profiles: Have winter and summer variations
Product Comparison: Compare newly received products against owned ones
Backup/Export: Export the inventory and routine as JSON ro CSV so its never dependent on the AI service to acess data
Inventory Source of Truth: If receiving new products the application already knows the other products owned and which days they're scheduled so that that information doesn't need to be repeatedly explained to the AI.
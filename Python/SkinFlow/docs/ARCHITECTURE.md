# SkinFlow architecture

## Architecture through Phase 2

```text
src/skinflow/
  app.py                  CLI options, logging, database startup, QApplication
  database.py             SQLite engine, session factory, upgrades, backup
  models.py               Products, plan, plan revisions, completions, settings
  seed.py                 Supplied products and editable baseline (seed once)
  current_routine.py      One-time current configuration, evidence tags, preserved templates
  services.py             Inventory validation and deterministic schedule operations
  schedule_formats.py     Versioned two-session conversion used by migration and legacy reads
  tracking.py             Observations, region states, temporal completion context
  safety/
    tags.py               Explicit evidence-aware product tags
    engine.py             Pure rules, findings, personal caution policy
    service.py            Read-only adapter for plans, actual use, and observations
  migrations/
    env.py                Shared-connection Alembic configuration
    versions/0001_initial.py
    versions/0002_safety_tracking.py
    versions/0003_two_daily_sessions.py
  ui/
    window.py             Shell, navigation, themes
    pages.py              Dashboard, inventory, calendar, settings
    dialogs.py            Product, ordered routine, step, monthly editors
    safety_views.py       Warning details and explicit local change approval
    tracking_views.py     Observation editor and actual-use timeline
    common.py             Error handling and confirmation helpers
tests/                    Domain, persistence, offline, and pytest-qt tests
scripts/                  Windows build entry point and PyInstaller driver
```

Qt views use services; services own validation and transactions. The database module owns connection
configuration. Domain code never imports Qt, so it can be tested without a GUI. No AI or network
library is imported at runtime through Phase 2.

## Storage decisions

| Record | Purpose |
| --- | --- |
| `products` | Attributes, full ingredient verification, evidence-tag JSON, status, deletion tombstone |
| `plans` | Current facial/scalp routines, monthly rules/decisions, overrides, version counter |
| `plan_revisions` | Append-only complete schedule snapshots with time and change description |
| `completions` | Actual date/period/step, product reference, historical label, completion timestamp |
| `settings` | Seed marker and preferences; never API credentials |
| `observations` | Date, region, condition, severity, notes, photo path, concerning flags, resolution |
| `routine_templates` | Original baseline, previous plan, and the supplied current configuration |
| `alembic_version` | Current schema revision |

Weekly keys are `weekday:period` with Monday = 0; periods are AM and Night (evening/nighttime).
Override keys are `YYYY-MM-DD:period`. Historical PM, Midday, and Evening data normalize to Night
at read/restore time. Old revision JSON and completion labels/timestamps are not rewritten.
Legacy completion records remain accessible in the Night view.
Steps carry stable UUIDs, labels, product IDs, optional/review flags, directions, skip conditions,
region, frequency notes, and substitution product IDs.
Monthly rules carry stable IDs, ordinal 1–5, weekday, period, enabled flag, and ordered steps.
Monthly step IDs are namespaced by rule ID when materialized.

Schedule resolution: a date override replaces the session; otherwise resolve the weekly routine
and append/replace matching monthly rules. Review-required rules remain reminders until a stored
occurrence decision approves them. Approval previews the treatment and owned recovery overrides;
skipping restores only owned changes, preserving later manual edits. Resolution never writes
completions. Facial and scalp schedules have separate weekly/override maps. Moving scalp/shower
care changes shower flags without moving facial product steps.

Each schedule mutation and its new revision commit in one transaction. The plan's version counter
prevents stale editors from replacing a newer plan. Rollback copies a selected revision into a new
revision. Product names on routine steps and completions are snapshots; these remain meaningful
after product changes. Deletion is a tombstone, not cascading deletion.

SQLite foreign keys are enabled on each connection. Python's modern transaction handling is enabled
explicitly. SQLAlchemy connections use a five-second busy timeout. Backups use SQLite's backup API
instead of copying a potentially active file. Dates use the computer's local date; completion/revision
timestamps use UTC, with local-time display in version history.

## Migration policy

Startup backs up an existing database before a schema upgrade, then calls Alembic `upgrade head`
before seeding. Revision `0001` defines an independent schema
snapshot using Alembic operations, rather than importing mutable models to create tables. Alembic
uses the application's connection and bundled migration folder, so no external `alembic.ini` is needed.

Revision `0002` adds product tags, observations, templates, and wider completion session names.
The current-configuration seed has its own marker; its one-time installation preserves previous
plans/templates/revisions and never resets edits on later launches. Missing products are not recreated.

Revision `0003` converts stored plans and templates to two sessions and records a new plan revision.
The versioned pure converter retains stable step IDs, combines nonempty sessions in their prior
order, resolves old date overrides against sibling sessions, and carries recovery ownership and
restoration data forward. Scoped legacy monthly replacements preserve unrelated combined steps.
It marks combined sessions for order review. Historical revisions and actual completion rows stay
intact. The frozen `collapse_sessions_v1` conversion is shared by the migration and legacy reads;
add a new versioned converter for future format changes instead of changing its semantics.
Database downgrade across this conversion requires restoring the pre-upgrade backup.

## Safety and observations

The pure engine accepts data objects and returns findings. The adapter expands a review window
by seven days on either side, resolves the schedule, and merges distinct logged use removed from
that plan. Planned and completed references to the same step do not double-count exposure.
Ordering checks use planned order rather than guessing an order for removed completed products.
No review writes data. Local proposals commit only through explicit approval with the expected
schedule version; cancellation and stale approval leave the plan unchanged.

The latest observation per region determines the state at each date, until resolution or a newer
state. Future observations are excluded. The tracker associates records with nearby actual
completions without inferring causation. Photos are local references. See
[Safety rules](SAFETY_RULES.md) for evidence boundaries, numeric preferences, and primary references.

For schema changes: back up existing data; add a versioned script with a unique `revision` and the
previous `down_revision`; use `op.batch_alter_table` for SQLite table changes; update the models;
test upgrade from a database at the preceding revision and check persistence. Do not edit a released
migration. Schema downgrade is a developer operation; schedule rollback does not downgrade schemas.

## Implementation plan

See [Implementation Plan.md](../Implementation%20Plan.md) for the phase checklist,
remaining work, and acceptance criteria.

## Current limits

The schedule JSON is internal, service-validated data, not a public import or AI proposal schema.
The recent completion table displays the latest 200 records. Image paths reference existing files;
database backups do not include image files. The app does not prevent multiple instances, but schedule
editor version checks prevent stale saves; product edits currently use last-write-wins semantics.
Unexpected failures are logged with a user-visible error. Tests isolate databases and network access;
offscreen GUI tests complement, rather than replace, final Windows visual and packaging checks.

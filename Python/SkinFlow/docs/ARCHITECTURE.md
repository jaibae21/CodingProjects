# SkinFlow architecture

## Phase 1 architecture

```text
src/skinflow/
  app.py                  CLI options, logging, database startup, QApplication
  database.py             SQLite engine, session factory, upgrades, backup
  models.py               Products, plan, plan revisions, completions, settings
  seed.py                 Supplied products and editable baseline (seed once)
  services.py             Inventory validation and deterministic schedule operations
  migrations/
    env.py                Shared-connection Alembic configuration
    versions/0001_initial.py
  ui/
    window.py             Shell, navigation, themes
    pages.py              Dashboard, inventory, calendar, settings
    dialogs.py            Product, ordered routine, step, monthly editors
    common.py             Error handling and confirmation helpers
tests/                    Domain, persistence, offline, and pytest-qt tests
scripts/                  Windows build entry point and PyInstaller driver
```

Qt views use services; services own validation and transactions. The database module owns connection
configuration. Domain code never imports Qt, so it can be tested without a GUI. No AI or network
library is imported at runtime in Phase 1.

## Storage decisions

| Record | Purpose |
| --- | --- |
| `products` | Full product attributes, verification flag, status, and deletion tombstone |
| `plans` | Single current plan: JSON weekly routines, monthly rules, date overrides, version counter |
| `plan_revisions` | Append-only complete schedule snapshots with time and change description |
| `completions` | Actual date/period/step, product reference, historical label, completion timestamp |
| `settings` | Seed marker and preferences; never API credentials |
| `alembic_version` | Current schema revision |

Weekly keys are `weekday:period` with Monday = 0. Override keys are `YYYY-MM-DD:period`.
Steps carry stable UUIDs, labels, optional product IDs, optional flags, and review flags.
Monthly rules carry stable IDs, ordinal 1–5, weekday, period, enabled flag, and ordered steps.
Monthly step IDs are namespaced by rule ID when materialized.

Schedule resolution: a date override replaces everything for that period; otherwise copy the weekly
routine and append matching monthly steps. Resolution never writes completions. Moving a routine
creates explicit source/target overrides, leaving completed records and recurring rules intact.

Each schedule mutation and its new revision commit in one transaction. The plan's version counter
prevents stale editors from replacing a newer plan. Rollback copies a selected revision into a new
revision. Product names on routine steps and completions are snapshots; these remain meaningful
after product changes. Deletion is a tombstone, not cascading deletion.

SQLite foreign keys are enabled on each connection. Python's modern transaction handling is enabled
explicitly. SQLAlchemy connections use a five-second busy timeout. Backups use SQLite's backup API
instead of copying a potentially active file. Dates use the computer's local date; completion/revision
timestamps use UTC, with local-time display in version history.

## Migration policy

Startup calls Alembic `upgrade head` before seeding. Revision `0001` defines an independent schema
snapshot using Alembic operations, rather than importing mutable models to create tables. Alembic
uses the application's connection and bundled migration folder, so no external `alembic.ini` is needed.

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

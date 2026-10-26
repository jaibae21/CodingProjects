# SkinFlow

A local-first Windows desktop app for a personal skincare inventory and editable AM/PM routines.
Python 3.12+, PySide6, SQLAlchemy, and SQLite. **Phases 1 and 2 are implemented.**

## Project documentation

- [Implementation plan](Implementation%20Plan.md): phase status, tasks, and acceptance criteria.
- [Agent guide](AGENT.md): development workflow, virtual environment commands, and project rules.
- [Architecture](docs/ARCHITECTURE.md): modules, storage decisions, and migration policy.
- [Current routine](docs/CURRENT_ROUTINE.md): the October 25, 2026 configuration.
- [Safety rules](docs/SAFETY_RULES.md): evidence, preferences, and limitations.
- [Testing notes](docs/TESTING_NOTES.md): feedback and follow-up verification.

## Start the app

From this repository's root in PowerShell, using the virtual environment already created:

```powershell
cd C:\Users\tonka\CodingProjects\Python\SkinFlow
.\.venv\Scripts\python.exe -m skinflow
```

Or double-click `launch.cmd`. No activation, API key, or internet connection is needed to run it
after dependencies are installed. The first launch creates and seeds the local database automatically.

To install on another checkout (Python 3.12 or newer must be on PATH):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m skinflow
```

`requirements-dev.lock.txt` records the exact Windows/Python 3.13 development environment tested
for this version. To reproduce it, install that file before installing this project:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps -e .
```

## What works

- **Today:** choose a date, Morning or Night, and Face/Scalp. See ordered steps,
  product directions, shower/override indicators, warnings, completions, and the next treatment.
- **Product shelf:** all 24 supplied products, searchable by brand/name/actives and filterable by
  category/status. Add, edit, archive, pause, or delete products. Edit ingredients, verification,
  purpose, instructions, frequency, suitability, opened/expiry dates, PAO notes, image path, and notes.
  Images are previewed in the editor; their original local files must stay available.
- **Routine calendar:** Morning and Night sessions, separate scalp care, ordered steps, skip conditions,
  substitution choices, shower flags, monthly review, one-off edits, moves, and rollback.
- **Skin tracker:** dated region states, severity, notes, local photos, resolution, and a timeline
  beside products actually used on or up to three days before each observation.
- **Offline safety:** evidence-aware product tags and warnings for irritant overlaps, skin regions,
  treatment spacing, frequency, sun protection, ordering, and incomplete ingredient data.
- **Settings:** light/dark themes with explicit dropdown colours, personal caution thresholds,
  and a consistent SQLite backup.
- Automatic Alembic schema upgrades, transactional writes, file logging, and automated GUI tests.

## Edit a routine

1. Open **Routine calendar**, choose **Face** or **Scalp**, and select a session cell.
2. Choose **Only this date** for a one-off override, or **Every week (base schedule)** for a
   recurring change. Double-click the cell or choose **Edit selected routine**.
3. Edit products, labels, directions, skip conditions, and substitution choices; reorder using ↑ / ↓.
   Select a substitute in the product dropdown to replace the step. Listing alternatives does not
   schedule additional products.
4. Save. Use **Clear date override** to resume the weekly/monthly plan for that date.

Monthly rules can append or replace a session. A fifth weekday runs only in months that have it.
A date override replaces that session, including monthly additions. A review-required treatment
stays a reminder until you approve that occurrence.

**Move to another date** creates two one-off overrides: an empty source and a copy at the target.
It replaces the target session, after review of the changes and warnings. Other periods and the
recurring plan stay as they were. Completions remain on their actual dates. Move a **Scalp** session
to move shower/scalp care without moving or duplicating facial retinol.

**Version history** restores the weekly plan, monthly rules, and one-off overrides together.
Restoring creates a new version, so the change itself can be rolled back. It does not alter products
or completion records. An editor rejects saves if another window has changed the plan in the meantime.

## Current routine and recovery

The supplied current schedule is installed once into SQLite, including Sunday Night Sungboon
retinol and Saturday Night mask alternatives. The original baseline and the previously saved
plan remain under **Saved routine templates** and in history. Templates require review before
replacing a plan. Subsequent launches preserve your edits.

Select the first Saturday and choose **Monthly occurrence** to review the optional AHA/BHA
treatment or skip it. Approval replaces the mask and proposes recovery overrides for Thursday/Friday
before and Sunday/Monday after. Cancel changes nothing. Skipped actives are not rescheduled.
Skipping an already approved occurrence restores its generated overrides while preserving later
manual edits.

**Recovery override** proposes a temporary plan for a date and up to seven days on either side.
It removes recorded irritants and fills cleanser/moisturizer gaps from available inventory, keeping
sunscreen last. Review the exact products and tolerance before approval. Missing ingredients cannot
establish that retained products are suitable for your skin.

## Observations and warnings

Record Normal, Dry, Red/Irritated, Stinging/Burning, Active Acne, Recovering, or Other states per
region. The latest state applies until resolved or replaced; Normal clears a previous state.
Historical reviews ignore future observations. The timeline shows actual completions without
claiming causation.

Product editors include safety tags with user-reported or label-verified evidence, separate from
full ingredient verification. Actives text is not automatically converted into evidence. Inactive
products remain visible in plans but are excluded from planned exposures and disabled on the dashboard.

Use **Review warnings** for severity, explanations, alternatives, affected sessions/regions, and
evidence. Hover findings for rule IDs/source links. Spacing and frequency settings are configurable
personal preferences, not universal medical limits. Reviews include actual use removed from plans.

## Supplied data and boundaries

The seed is the user's brief and configuration, not a verified catalogue. Missing details
are left blank and shown as unknown/unverified. Retinol and acid descriptions come only from the
supplied names and notes. Morning retains an unconfirmed SPF 30+ reminder as requested in the latest
configuration. SPF 15 does not satisfy confirmed SPF 30+ protection. Saturday defaults to Pureal with
two mask substitution choices.

The first Saturday starts as a review reminder. Only approval schedules the strong peel. Routine
labels no longer repeat "if tolerated"; skip conditions and directions retain precautions. Checking
a reminder records that reminder, not confirmed sunscreen or treatment application.

The AI assistant remains planned in [the implementation plan](Implementation%20Plan.md).
No external requests are made by
the app. The OpenAI SDK, model selection, pricing documentation, data-sharing choices, structured
proposals, approval workflow, and mocked API failure tests belong to Phase 3.

## Data, backups, and logs

Default Windows location: `%LOCALAPPDATA%\SkinFlow\skinflow.db`.
The database and rotating `skinflow.log` files stay outside the source checkout and virtual environment.
For a separate profile or experiment:

```powershell
.\.venv\Scripts\python.exe -m skinflow --data-dir .\my-local-data
```

Alternatively set `SKINFLOW_DATA_DIR`. The command-line option takes precedence.
The example `.env.example` is documentation; the app does not load `.env` files.

Before upgrading a Phase 1 database, the app saves `skinflow-pre-upgrade-*.db` beside it. The
one-time current-routine configuration also preserves the previous plan as a template, all prior
revisions, and actual completions. Subsequent launches do not reset edits.

Migration `0003` reduces existing plans and templates to Morning and Night. Former Midday and
Evening steps move into Night, preserving their IDs, order, date overrides, monthly decisions,
and shower flags. Combined nonempty sessions are marked for an order review. Historical revisions
and actual completion labels/timestamps are retained; legacy records remain accessible through Night.
The pre-upgrade backup retains the original database. New schedules have only two daily sessions.

Product deletion hides a retained database row so schedule references and recorded product names
survive. It is not permanent erasure of personal data. Completion labels are historical snapshots;
later product edits never rewrite them. Routine labels are also explicit, editable snapshots.
Archived, paused, testing, and deleted products are identified on the dashboard; archiving does not
silently rewrite schedules.

Use **Settings → Save database backup** to save a consistent copy. Image files are external references
and must be backed up separately. To restore manually, **close every SkinFlow window**, keep a copy
of the current database, then copy your backup to `skinflow.db` in the data folder. Relaunch the app.
A guided restore and portable JSON import/export are planned for Phase 4.

## Run checks in the virtual environment

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m ruff format --check src tests scripts
```

Tests use temporary databases and Qt's offscreen platform. They do not open or modify your real
inventory. Tests cover inventory validation, seeding, archiving/deletion, weekly/monthly recurrence,
overrides/moves, revisions/rollback, independent completions, stale edits, restart persistence,
database backups, offline services, and GUI editing/navigation/search/themes. Phase 2 adds rule
boundaries, region states, two daily sessions, separate scalp moves, approval/cancellation,
dropdown palettes, and upgrades from older schemas. The current suite has 94 tests.

## Windows executable build

The build script is provided for the packaging phase; an executable has not been built or validated
as part of Phases 1–2. From the project virtual environment on Windows:

```powershell
.\.venv\Scripts\python.exe scripts\build_windows.py
```

It runs tests, then uses PyInstaller to produce `dist\SkinFlow\SkinFlow.exe`. Distribute the **whole
SkinFlow folder**, including `_internal`. The build bundles migration files; data still lives under
the user's local application data folder. Test packaged startup, backup, and upgrades on a clean
Windows machine before release.

## Reference documentation

Implementation references: [SQLAlchemy SQLite](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html),
[Alembic programmatic connections](https://alembic.sqlalchemy.org/en/latest/cookbook.html#sharing-a-connection-across-one-or-more-programmatic-migration-commands),
and [pytest-qt](https://pytest-qt.readthedocs.io/en/latest/tutorial.html).

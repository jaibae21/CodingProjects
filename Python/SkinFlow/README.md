# SkinFlow

A local-first Windows desktop app for a personal skincare inventory and editable AM/PM routines.
Python 3.12+, PySide6, SQLAlchemy, and SQLite. **Phase 1 is implemented.**

## Project documentation

- [Implementation plan](Implementation%20Plan.md): phase status, tasks, and acceptance criteria.
- [Agent guide](Agent.md): development workflow, virtual environment commands, and project rules.
- [Architecture](docs/ARCHITECTURE.md): modules, storage decisions, and migration policy.

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

## What works in Phase 1

- **Today:** choose a date and AM/PM, see ordered steps and shower/override indicators, mark steps
  completed, see recent completion history and the next planned treatment or review reminder.
- **Product shelf:** all 24 supplied products, searchable by brand/name/actives and filterable by
  category/status. Add, edit, archive, pause, or delete products. Edit ingredients, verification,
  purpose, instructions, frequency, suitability, opened/expiry dates, PAO notes, image path, and notes.
  Images are previewed in the editor; their original local files must stay available.
- **Routine calendar:** weekly AM/PM view, ordered step editor with add/edit/remove and move up/down,
  shower flags, editable monthly recurrence, one-off edits, date moves, and version history/rollback.
- **Settings:** persistent light/dark theme and a consistent SQLite backup.
- Automatic Alembic schema upgrades, transactional writes, file logging, and automated GUI tests.

## Edit a routine

1. Open **Routine calendar** and select an AM or PM cell.
2. Choose **Only this date** for a one-off override, or **Every week (base schedule)** for a
   recurring change. Double-click the cell or choose **Edit selected routine**.
3. Add products or reminders, edit their labels, set optional/review flags, and reorder using ↑ / ↓.
4. Save. Use **Clear date override** to resume the weekly/monthly plan for that date.

Monthly treatments append their steps to the weekly routine on the selected ordinal weekday.
A fifth weekday only runs in months that have that occurrence. A one-off override replaces the
entire AM/PM routine for its date, including monthly additions. To put monthly steps elsewhere in
the application order, edit that date's routine and reorder them.

**Move to another date** creates two one-off overrides: an empty source and a copy at the target.
It replaces the target AM/PM plan. The other period and weekly baseline stay as they were.
Completed activities remain on their actual dates.

**Version history** restores the weekly plan, monthly rules, and one-off overrides together.
Restoring creates a new version, so the change itself can be rolled back. It does not alter products
or completion records. An editor rejects saves if another window has changed the plan in the meantime.

## Supplied data and boundaries

The seed is the user's brief, not a verified product catalogue. Ingredient lists and missing details
are left blank and shown as unknown/unverified. Retinol and acid descriptions come only from the
supplied names and notes. No sunscreen is invented: AM has an SPF 30+ reminder because a sunscreen
product is unconfirmed. Alternative moisturizers and the unspecified hydrating mask are labelled
explicitly; edit a step to associate the exact product you choose.

The first Saturday has a **caution/review reminder** for the historical strong peel. It is not an
instruction to use it and has no associated application product. Optional steps are suggestions
from the brief; checking a reminder records completion of that reminder.

Ingredient interaction rules, automatic conflict checks after moves, recovery-day assistance,
skin observations, and the AI assistant are **not implemented in Phase 1**. These are tracked in
[the implementation plan](Implementation%20Plan.md). No external requests are made by
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
The example `.env.example` is documentation; Phase 1 does not load `.env` files.

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
database backups, offline services, and GUI editing/navigation/search/themes.

## Windows executable build

The build script is provided for the packaging phase; an executable has not been built or validated
as part of Phase 1. From the project virtual environment on Windows:

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

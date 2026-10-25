# SkinFlow agent guide

## Start here

Read [README.md](README.md), [Implementation Plan.md](Implementation%20Plan.md), and
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) before changing the project.
The application is a local-first Windows desktop app using Python 3.12+, PySide6,
SQLAlchemy, SQLite, and Alembic. Phase 1 is implemented; later phases remain planned.

## Workspace and branch

- Keep this project under `Python/SkinFlow` in the shared CodingProjects repository.
- The initial development branch is `feature/skinflow-phase-1`. Inspect the current branch
  and working tree before editing; preserve unrelated changes.
- Keep changes on the task's development branch. Do not switch branches, commit, merge,
  publish, or start a later phase solely because this guide lists those actions.
- Keep application data and generated artifacts out of Git. Never commit `.venv`, API keys,
  `.env`, databases, logs, user photos, or build output.

## Python environment

Run development, installation, tests, and builds with the project's virtual environment.
From `Python/SkinFlow` in PowerShell:

```powershell
# Only if the environment does not exist yet:
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"

# Launch with a separate disposable data folder for manual development:
.\.venv\Scripts\python.exe -m skinflow --data-dir .validation\manual

# Automated checks:
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check src tests scripts
.\.venv\Scripts\python.exe -m ruff format --check src tests scripts
```

Use temporary databases and mocked external services in tests. Do not run tests against
the real `%LOCALAPPDATA%\SkinFlow` profile. Qt tests use the offscreen platform configured
in `tests/conftest.py`; unexpected warning/error dialogs fail tests instead of blocking them.
Add meaningful tests for changed behavior, particularly scheduling, persistence, validation,
and GUI interactions. Do not make live API calls during automated tests.

## Architecture and persistence rules

- Keep Qt code in `ui/`; put validation and transactional operations in services.
- Keep scheduling and safety evaluation deterministic and independent of AI and Qt.
- Add type hints to service interfaces and handle failures with useful logging and UI feedback.
- For schema changes, add a new Alembic revision and upgrade tests. Do not rewrite a
  released migration or replace migrations with `create_all` during normal startup.
- Preserve the separation between planned routines and actual completions. Moving or
  rolling back a plan must not move or delete actual completion records.
- Keep historical labels and product references meaningful after product edits/deletion.
- Keep weekly edits, monthly additions, and one-off overrides distinct. A date override
  replaces the full routine for that period; monthly steps otherwise append to the baseline.
- Save schedule changes and their revisions together. Preserve optimistic version checks
  so a stale editor cannot silently replace a newer plan.
- Seed only once. Never recreate products a user has deleted or overwrite their edits.
- Use SQLite's backup API for active databases. Restore only after closing app connections;
  keep the previous database before replacing it.

## Product information and safety

Do not invent ingredient lists, concentrations, verification, or usage instructions.
Keep unknown information explicitly unverified. The historical strong peel starts as a
caution/review reminder, not an automatic recommendation to apply it.

Future safety findings must distinguish established concerns from conservative preferences,
explain severity and alternatives, and avoid diagnosis or claims of medical causation.
Keep core inventory and routine management available without internet or AI credentials.

## Future AI work

Before implementing Phase 3, consult current official OpenAI documentation and the
OpenAI documentation skill if available. Use the Python SDK and Responses API with
validated structured proposals, explicit timeouts, and configurable model selection.
Document current model costs when that integration is implemented.

Let the user choose which local details are sent. Keep credentials in environment variables
or the operating-system credential store, never SQLite, prompts, logs, exports, or Git.
The AI must not execute arbitrary database updates. Require explicit approval of each
proposed routine change, then validate references, safety findings, and the plan version
before applying it through the schedule service. API failure or rejection leaves plans intact.

## Handoff

Update the README, implementation checklist, and architecture when behavior or scope changes.
Report what changed, checks actually run, and remaining limitations. Distinguish source startup
and offscreen GUI checks from a validated Windows executable; packaging is still planned.

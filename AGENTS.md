# Repository Guidelines

## Project Structure & Module Organization
- `binja/` contains Binary Ninja plugin scripts (`binja_export.py`, `binja_import.py`).
- `ida/` contains IDA Pro scripts (`ida_export.py`, `ida_import.py`).
- `screenshots/` holds GIFs referenced by `README.md`.
- `plugin.json` defines Binary Ninja plugin metadata and versioning.

## Build, Test, and Development Commands
- No build step; scripts are loaded directly by Binary Ninja or IDA.
- Dependency setup: `uv sync --extra dev`.
- Manual usage:
  - Binary Ninja: `Plugins -> bnida -> Export/Import analysis data`.
  - IDA: run `ida_export.py`/`ida_import.py` via `Alt+F7` or install them in the plugins directory.
- Optional syntax check: `python -m py_compile binja/*.py ida/*.py`.
- Unit tests: `uv run pytest`.

## Coding Style & Naming Conventions
- Python 3, 4-space indentation, and PEP 8-ish formatting.
- Use `snake_case` for functions/variables and `CapWords` for classes.
- Repository history shows formatting via `yapf`; keep formatting consistent if you use it.

## Testing Guidelines
- Unit tests run under `pytest` with `binja-test-mocks`.
- Validate changes manually by exporting a JSON file from one tool and importing into the other.
- Confirm functions, names, comments, and structs import correctly and remain stable after rebasing.

## Commit & Pull Request Guidelines
- Recent commits use short, imperative summaries; some use `type: summary` (e.g., `feat: ida 9 support`).
- Prefer `feat:`, `fix:`, or `chore:` when it fits; otherwise keep the message concise and action-oriented.
- PRs should include:
  - a clear description of behavior changes and affected Binja/IDA versions,
  - manual validation steps or sample workflows,
  - updated assets in `screenshots/` if user-visible flows change.

## Configuration Notes
- Update `plugin.json` `version` and `minimumbinaryninjaversion` only when a release or compatibility shift requires it.

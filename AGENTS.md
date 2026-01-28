# Repository Guidelines

## Project Structure & Module Organization
The Python package lives in `src/simcache/`, with modules like `core.py`, `store.py`, and `iterations.py`. Tests are intended to live in `tests/`, and runnable usage scripts or demos belong in `examples/`. Repository metadata (license, packaging, and high-level docs) sit at the root alongside `LICENCE`, `pyproject.toml`, and `README.md`.

## Build, Test, and Development Commands
This repo does not yet define a build or test toolchain in `pyproject.toml`. Use the following conventions while the project is bootstrapped:
- `python -m pip install -e .` for an editable install during development.
- `python -m pytest tests` once tests are implemented and `pytest` is added.
- `python examples/plot.py` for running example scripts (adjust to the script you are working on).

## Coding Style & Naming Conventions
Use 4-space indentation, keep modules and functions in `snake_case`, and classes in `PascalCase`. Prefer explicit, descriptive names that match their module (`store.py` should contain store-related APIs). Keep CLI-related code in `src/simcache/cli.py` to avoid scattering entry points.

## Testing Guidelines
Place tests in `tests/` and mirror module names where possible (e.g., `tests/store.py` covering `src/simcache/store.py`). Keep tests deterministic and fast. When a test framework is established, document any fixtures, markers, or coverage thresholds here.

## Commit & Pull Request Guidelines
There is no Git history yet, so no enforced commit format exists. Use short, imperative commit summaries (e.g., “Add cache eviction strategy”) and keep commits focused. For pull requests, include a clear description of behavior changes, how you tested them, and any follow-up work or known limitations.

## Configuration & Data Hygiene
Avoid committing large datasets or generated artifacts. If new configuration or secrets are required, add a sample file and document environment variables in `README.md`.

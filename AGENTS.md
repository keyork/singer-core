# AGENTS.md — Singer-Core

## Project Overview

Singer-Core is a Python data collection tool using Playwright-based request interception to scrape structured data at scale (~34K records). Licensed under Apache 2.0.

**Current state**: Fully implemented. 7 source modules, 27 tests passing.

## Architecture

- **Target API**: POST to `REQUEST_URL` with `application/x-www-form-urlencoded` body (`current=X&size=10`)
- **Auth headers**: `X-Auth-Key`, `X-Auth-Timestamp`, `X-Auth-Nonce`, `X-Auth-Signature`
- **Signature**: `MD5(key + secret + timestamp + nonce)` — signatures do NOT bind to payload
- **Auth Key capture**: Automatically extracted from frontend request headers on first intercepted request; no manual config needed
- **Approach**: Playwright request interception (`page.route`) to modify POST data without DOM interaction
- **Export**: CSV with `utf-8-sig` encoding, all API fields auto-collected (not limited to a predefined set)
- **Resume**: Track progress via `progress.txt` for fault tolerance
- **Rate limiting**: `asyncio.sleep(random.uniform(2.5, 3.5))` between pages
- **Anti-detection**: Custom UA, `--disable-blink-features=AutomationControlled`, `wait_until="commit"`

## Project Structure

```
singer-core/
├── src/
│   └── singer_core/          # Main package
│       ├── __init__.py       # Package version
│       ├── __main__.py       # CLI entry point (rich logging + summary)
│       ├── config.py         # pydantic-settings config from .env
│       ├── auth.py           # Signature generation (MD5)
│       ├── scraper.py        # Playwright request interception engine
│       ├── exporter.py       # CSV append writer (utf-8-sig)
│       └── progress.py       # Checkpoint/resume logic
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_scraper.py
│   ├── test_exporter.py
│   └── test_progress.py
├── pyproject.toml             # Project config, deps, tool settings
├── .env                       # Target URLs + auth secret (gitignored)
├── .gitignore
├── LICENSE
├── README.md
└── AGENTS.md
```

## Build / Lint / Test Commands

**Setup** (use uv — preferred over pip/poetry):

```bash
uv sync                        # Install dependencies
uv run playwright install      # Install browser binaries
```

**Run**:

```bash
uv run python -m singer_core   # Main CLI
```

**Test**:

```bash
uv run pytest                          # All tests
uv run pytest tests/test_auth.py       # Single test file
uv run pytest tests/test_auth.py::test_signature_generation  # Single test
uv run pytest -x                       # Stop on first failure
uv run pytest --cov=singer_core        # With coverage
uv run pytest -q tests/test_exporter.py  # Quick single-file run
```

**Lint & Format**:

```bash
uv run ruff check .            # Lint
uv run ruff check --fix .      # Lint with auto-fix
uv run ruff format .           # Format
```

**Type Check**:

```bash
uv run mypy src/singer_core
```

## Code Style Guidelines

### Python Version

- Target Python 3.11+

### Imports

- Use absolute imports: `from singer_core.config import load_config`
- stdlib → third-party → local, separated by blank lines
- No wildcard imports (`from module import *`)
- Use `from __future__ import annotations` in all source files

### Formatting (Ruff defaults)

- Line length: 88 (Black-compatible)
- Double quotes for strings
- Trailing commas in multi-line collections
- Use `f-strings` for string formatting, not `%` or `.format()`

### Naming

- Files: `snake_case.py`
- Classes: `PascalCase` (e.g., `ScraperEngine`, `CsvExporter`)
- Functions/variables: `snake_case` (e.g., `generate_signature`, `page_count`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_PAGE_SIZE`, `AUTH_SECRET`)
- Private members: leading underscore `_internal_method`

### Type Annotations

- Annotate all function signatures (params and return types)
- Use `dict[str, Any]` not `Dict[str, Any]` (modern syntax)
- Use `str | None` not `Optional[str]`
- Use `pydantic` models for structured config/data, not raw dicts
- Run `mypy --strict` with zero errors

### Error Handling

- Create custom exceptions in a dedicated module or at package top
- Use specific exception types, never bare `except:`
- Always include context in error messages
- Use `logging` module, never `print()` for diagnostics
- Log levels: `DEBUG` (request/response details), `INFO` (progress), `WARNING` (retries), `ERROR` (failures)

### Async Patterns

- Use `asyncio` with `async/await` throughout
- Playwright APIs are async — do not wrap in sync
- Use `async with` for resource management (browser contexts, pages)
- Rate-limit requests with `asyncio.sleep()` between pages

### Environment & Config

- Load secrets and URLs from `.env` via pydantic-settings
- Never hardcode URLs, keys, or credentials in source
- Provide sensible defaults in `config.py` for non-sensitive values

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `BASE_URL` | Target site page URL | Yes | — |
| `DETAIL_URL` | Detail page URL template | Yes | — |
| `REQUEST_URL` | API endpoint URL | Yes | — |
| `AUTH_KEY` | X-Auth-Key (auto-captured if empty) | No | `""` |
| `AUTH_SECRET` | MD5 signature salt | No | `ylfwxxpt` |
| `PAGE_SIZE` | Records per page | No | `10` |
| `DELAY_SECONDS` | Delay between pages (base) | No | `1.0` |
| `OUTPUT_DIR` | CSV output directory | No | `output` |
| `OUTPUT_FILENAME` | CSV filename | No | `data.csv` |
| `PROGRESS_FILE` | Checkpoint file path | No | `progress.txt` |
| `EXPORT_FIELDS` | JSON list of field names | No | 6 default fields |
| `EXPORT_HEADERS` | JSON map field→header | No | 6 default mappings |

## Testing Conventions

- Framework: `pytest` with `pytest-asyncio` for async tests
- Test files: `test_<module>.py` in `tests/` directory
- Test functions: `test_<behavior>` (e.g., `test_signature_md5_format`)
- Fixtures: shared fixtures in `conftest.py`
- Mocking: use `pytest-mock` (`mocker` fixture) — avoid `unittest.mock` directly
- Playwright tests: mock all browser APIs, never open real browser in unit tests
- Target: high coverage on `auth.py`, `exporter.py`, `progress.py`; mock network in `scraper.py` tests

## Anti-Patterns (Do NOT Do)

- Never commit `.env` or credentials (it's gitignored — keep it that way)
- Never use `print()` for logging — use `logging` module or `console.print()`
- Never use synchronous Playwright APIs — always async
- Never suppress exceptions with empty `except` blocks
- Never use `# type: ignore` — fix the type error instead
- Never hardcode API keys, URLs, or page counts in source
- Never use `time.sleep()` in async code — use `asyncio.sleep()`
- Never include website names, domains, or real URLs in source code

## Commit Conventions

- Write clear, conventional commit messages
- Reference the issue or context when applicable
- Do not commit generated data files (CSV output, progress.txt, etc.)

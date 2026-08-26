# Pytest Automation Framework

## Setup

Create an environment and install the project dependencies:

```powershell
uv venv
uv pip install -e .
```

Activate the environment if you want to run `pytest` directly:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Run tests

```powershell
uv run pytest
```

## Configuration

The client reads these optional environment variables:

| Variable | Default | Purpose |
| --- | --- | --- |
| `API_BASE_URL` | `https://example.test` | API host used by requests |
| `API_TIMEOUT` | `10.0` | Request timeout in seconds |

Add endpoint tests under `tests/` and use the `api_client` fixture from `conftest.py`.

## Project structure

```text
framework/          Reusable API framework code
lib/                Shared project utilities
tests/              Test cases
conftest.py         Pytest fixtures and startup hooks
pyproject.toml      Project and pytest configuration
logs/               Generated log files; excluded from Git
```

Logging is configured in `lib/logging_config.py`. By default, test logs
are written to `logs/test.log`. Override the location or verbosity when needed:

```powershell
$env:LOG_FILE = "logs\smoke.log"
$env:LOG_LEVEL = "DEBUG"
python -m pytest
```

## Logging

Each test run writes logs to `logs/test.log`. Files are rotated at 5 MB and up to
three backup files are retained. Configure the destination and minimum level with:

```powershell
$env:LOG_FILE = "artifacts\api-tests.log"
$env:LOG_LEVEL = "DEBUG"
python -m pytest
```
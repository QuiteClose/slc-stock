from pathlib import Path

import pytest

from .helpers import Server

FORBIDDEN_ENV_VARS = [
    "ALPHA_VANTAGE_API_KEY",
    "POLYGON_API_KEY",
]


def _find_dotenv() -> Path:
    return Path(__file__).resolve().parent.parent.parent / ".env"


def _dotenv_has_credentials(env_file: Path) -> list[str]:
    """Return names of forbidden variables set in a .env file."""
    if not env_file.exists():
        return []

    found = []
    try:
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            key = line.split("=", 1)[0].strip()
            if key in FORBIDDEN_ENV_VARS:
                found.append(key)
    except Exception:
        pass
    return found


def _dotenv_has_content(env_file: Path) -> bool:
    """Return True if the file contains any non-comment, non-blank lines."""
    try:
        for line in env_file.read_text().splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                return True
    except Exception:
        pass
    return False


def pytest_configure(config):
    """Abort early if a real .env file is reachable.

    The Makefile shadows .env with /dev/null (empty file) inside the
    container, so an existing-but-empty .env is safe and allowed through.
    """
    env_file = _find_dotenv()
    if not env_file.exists():
        return

    if not _dotenv_has_content(env_file):
        return

    found = _dotenv_has_credentials(env_file)
    if found:
        raise pytest.UsageError(
            f"\n\n"
            f"ABORTING: .env file contains provider credentials!\n\n"
            f"The following variables are defined in {env_file}:\n"
            f"  {', '.join(found)}\n\n"
            f"Functional tests must run in an isolated environment without\n"
            f"access to real API keys. Use the Makefile which excludes .env:\n\n"
            f"    make test\n"
            f"    make test-notty\n"
        )

    raise pytest.UsageError(
        f"\n\n"
        f"ABORTING: .env file detected at {env_file}\n\n"
        f"Functional tests must run via the Makefile which excludes .env:\n\n"
        f"    make test\n"
        f"    make test-notty\n"
    )


@pytest.fixture(scope="session")
def server():
    """Empty server (no seed data) for the entire test session."""
    with Server() as s:
        yield s


@pytest.fixture(scope="session")
def seeded_server():
    """Server pre-populated with SEED_QUOTES for the entire test session."""
    srv = Server()
    srv._clean_db()
    srv.seed()
    srv._start_server()
    yield srv
    srv.__exit__(None, None, None)

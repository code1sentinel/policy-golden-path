from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"

try:  # the browser tests need Playwright: pip install -e ".[e2e]"
    import playwright.sync_api  # noqa: F401
except ImportError:
    collect_ignore = ["e2e"]


@pytest.fixture
def examples() -> Path:
    return EXAMPLES


@pytest.fixture(scope="module")
def examples_dir() -> Path:
    return EXAMPLES

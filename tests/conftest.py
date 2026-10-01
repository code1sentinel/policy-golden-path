from pathlib import Path

import pytest

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


@pytest.fixture
def examples() -> Path:
    return EXAMPLES


@pytest.fixture(scope="module")
def examples_dir() -> Path:
    return EXAMPLES

from pathlib import Path
import pytest

__CWD__ = Path(__file__).parent


@pytest.fixture
def flora_path() -> str:
    return str(__CWD__ / "data/demo-flora")

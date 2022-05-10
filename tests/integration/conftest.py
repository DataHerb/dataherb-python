from pathlib import Path
import pytest

__CWD__ = Path(__file__).parent


@pytest.fixture(scope="session")
def flora_path() -> Path:
    return __CWD__ / "data/demo-flora"

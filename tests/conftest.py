import pytest
from fastapi.testclient import TestClient
from superchat.app import create_app
from superchat.ai import AIProvider
from superchat.engine import Engine
from superchat.config import DATA_DIR


@pytest.fixture
def offline():
    provider = AIProvider()
    provider.key = ""
    return provider


@pytest.fixture
def client(tmp_path, offline):
    return TestClient(create_app(tmp_path / "logs", DATA_DIR, offline))


@pytest.fixture
def engine():
    return Engine(DATA_DIR)

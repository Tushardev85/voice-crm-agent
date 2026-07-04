import pytest
from fastapi.testclient import TestClient

import app as app_module


@pytest.fixture
def app():
    yield app_module.app


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)

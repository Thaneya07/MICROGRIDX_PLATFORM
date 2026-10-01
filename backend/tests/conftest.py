import os

import pytest
from fastapi.testclient import TestClient

# Ensure a DATABASE_URL is present for settings validation even if .env is
# not loaded in the test environment (CI, etc.).
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg2://microgridx:changeme@localhost:55432/microgridx"
)

from app.main import app  # noqa: E402


@pytest.fixture()
def client() -> TestClient:
    with TestClient(app) as test_client:
        yield test_client

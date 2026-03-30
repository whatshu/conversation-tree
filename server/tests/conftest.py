import os

os.environ["CT_DATABASE_URL"] = "sqlite:///./test.db"
os.environ["CT_ENABLE_MOCK_PROVIDER"] = "true"
os.environ["CT_API_TOKEN"] = "test-token"

import pytest
from fastapi.testclient import TestClient

from app.db.base import Base
from app.db.session import engine
from app.main import app


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)

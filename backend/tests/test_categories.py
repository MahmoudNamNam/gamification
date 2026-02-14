import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_categories_list():
    r = client.get("/categories")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    # If seed was run, we have categories; else empty
    for cat in data:
        assert "id" in cat
        assert "name_ar" in cat
        assert "name_en" in cat

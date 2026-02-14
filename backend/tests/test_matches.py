import pytest
import uuid
from unittest.mock import patch
from fastapi.testclient import TestClient
from bson import ObjectId

from app.main import app
from app.core.db import init_db, get_questions_collection

client = TestClient(app)


@patch("app.core.config.settings.RETURN_OTP_IN_RESPONSE", True)
def _register_and_token():
    email = f"match_{uuid.uuid4().hex[:12]}@example.com"
    r = client.post("/auth/register", json={"name": "M", "email": email, "password": "pass"})
    assert r.status_code == 200
    otp = r.json().get("otp")
    assert otp
    r2 = client.post("/auth/verify-otp/register", json={"email": email, "otp": otp})
    assert r2.status_code == 200
    return r2.json()["access_token"]


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_create_match_validation_more_than_six_categories():
    token = _register_and_token()
    r_cat = client.get("/categories")
    cats = r_cat.json()
    if len(cats) < 7:
        pytest.skip("Need at least 7 categories for test")
    ids = [c["id"] for c in cats[:7]]
    r = client.post(
        "/matches",
        json={
            "selected_category_ids": ids,
            "teamA_name": "A",
            "teamB_name": "B",
        },
        headers=_auth_headers(token),
    )
    assert r.status_code == 400
    data = r.json()
    assert "error" in data
    assert data["error"].get("code") == "MAX_CATEGORIES_EXCEEDED"


def test_create_match_success():
    token = _register_and_token()
    r_cat = client.get("/categories")
    cats = r_cat.json()
    if len(cats) < 1:
        pytest.skip("Need categories - run seed first")
    ids = [c["id"] for c in cats[:2]]
    r = client.post(
        "/matches",
        json={
            "selected_category_ids": ids,
            "teamA_name": "Team Alpha",
            "teamB_name": "Team Beta",
        },
        headers=_auth_headers(token),
    )
    assert r.status_code == 200
    data = r.json()
    assert "id" in data
    assert data.get("status") == "active"
    assert len(data.get("selected_category_ids", [])) == 2
    assert data.get("teams", {}).get("A", {}).get("name") == "Team Alpha"
    assert data.get("teams", {}).get("B", {}).get("name") == "Team Beta"


def test_next_question_respects_quota_and_used_questions():
    """Requesting a 3rd question for same category+level returns 409 LEVEL_QUOTA_EXCEEDED."""
    token = _register_and_token()
    r_cat = client.get("/categories")
    cats = r_cat.json()
    if len(cats) < 1:
        pytest.skip("Need categories - run seed first")
    cid = cats[0]["id"]
    init_db()
    qcol = get_questions_collection()
    existing = list(qcol.find({"category_id": ObjectId(cid), "level": 1, "status": "active"}))
    if len(existing) < 2:
        pytest.skip("Need at least 2 questions for category level 1 - run seed first")
    r = client.post(
        "/matches",
        json={"selected_category_ids": [cid], "teamA_name": "A", "teamB_name": "B"},
        headers=_auth_headers(token),
    )
    assert r.status_code == 200
    match_id = r.json()["id"]
    # Request first question
    r1 = client.post(
        f"/matches/{match_id}/next-question",
        json={"category_id": cid, "level": 1},
        headers=_auth_headers(token),
    )
    assert r1.status_code == 200
    # Request second question
    r2 = client.post(
        f"/matches/{match_id}/next-question",
        json={"category_id": cid, "level": 1},
        headers=_auth_headers(token),
    )
    assert r2.status_code == 200
    # Third request for same category+level must fail with LEVEL_QUOTA_EXCEEDED
    r3 = client.post(
        f"/matches/{match_id}/next-question",
        json={"category_id": cid, "level": 1},
        headers=_auth_headers(token),
    )
    assert r3.status_code == 409
    assert r3.json().get("error", {}).get("code") == "LEVEL_QUOTA_EXCEEDED"


def test_judging_updates_score_correctly():
    token = _register_and_token()
    r_cat = client.get("/categories")
    cats = r_cat.json()
    if len(cats) < 1:
        pytest.skip("Need categories - run seed first")
    cid = cats[0]["id"]
    r = client.post(
        "/matches",
        json={"selected_category_ids": [cid], "teamA_name": "A", "teamB_name": "B"},
        headers=_auth_headers(token),
    )
    assert r.status_code == 200
    match_id = r.json()["id"]
    rq = client.post(
        f"/matches/{match_id}/next-question",
        json={"category_id": cid, "level": 1},
        headers=_auth_headers(token),
    )
    if rq.status_code != 200:
        pytest.skip("No question available for category+level - run seed first")
    round_no = rq.json()["round_no"]
    points = rq.json()["points"]
    # Judge for TEAM_A
    rj = client.post(
        f"/matches/{match_id}/judge",
        json={"round_no": round_no, "judge_selection": "TEAM_A"},
        headers=_auth_headers(token),
    )
    assert rj.status_code == 200
    data = rj.json()
    assert data["scores"]["teamA"] == points
    assert data["scores"]["teamB"] == 0
    assert data["last_round"]["judge_selection"] == "TEAM_A"
    assert data["last_round"]["scored_points"] == points
    # Double-judge same round -> 409
    rj2 = client.post(
        f"/matches/{match_id}/judge",
        json={"round_no": round_no, "judge_selection": "TEAM_B"},
        headers=_auth_headers(token),
    )
    assert rj2.status_code == 409
    assert rj2.json().get("error", {}).get("code") == "ROUND_ALREADY_JUDGED"


def test_finish_returns_winner_or_draw():
    token = _register_and_token()
    r_cat = client.get("/categories")
    cats = r_cat.json()
    if len(cats) < 1:
        pytest.skip("Need categories - run seed first")
    cid = cats[0]["id"]
    r = client.post(
        "/matches",
        json={"selected_category_ids": [cid], "teamA_name": "Alpha", "teamB_name": "Beta"},
        headers=_auth_headers(token),
    )
    assert r.status_code == 200
    match_id = r.json()["id"]
    rf = client.post(f"/matches/{match_id}/finish", headers=_auth_headers(token))
    assert rf.status_code == 200
    data = rf.json()
    assert data["status"] == "finished"
    assert "scores" in data
    assert "teamA" in data["scores"] and "teamB" in data["scores"]
    assert "winner" in data
    assert data["winner"]["result"] in ("TEAM_A", "TEAM_B", "DRAW")
    if data["winner"]["result"] == "DRAW":
        assert data["winner"]["name"] is None
    else:
        assert data["winner"]["name"] in ("Alpha", "Beta")
    assert "summary" in data
    assert "teamA_correct" in data["summary"]
    assert "teamB_correct" in data["summary"]
    assert "no_one" in data["summary"]
    assert "total_rounds" in data["summary"]


def test_get_me_requires_auth():
    r = client.get("/me")
    assert r.status_code == 401

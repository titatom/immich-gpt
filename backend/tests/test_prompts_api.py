"""
Tests for /api/prompts router.

Covers: list (with filters), create, get, update, delete.
"""
import uuid

import pytest

from app.models.prompt_template import PromptTemplate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_prompt(db, prompt_type="global_classification", name="Test", enabled=True,
                 bucket_id=None) -> PromptTemplate:
    from tests.conftest import TEST_USER_ID
    pt = PromptTemplate(
        id=str(uuid.uuid4()),
        user_id=TEST_USER_ID,
        prompt_type=prompt_type,
        name=name,
        content="Do something useful.",
        enabled=enabled,
        version=1,
        bucket_id=bucket_id,
    )
    db.add(pt)
    db.commit()
    db.refresh(pt)
    return pt


# ---------------------------------------------------------------------------
# GET /api/prompts
# ---------------------------------------------------------------------------

def test_list_prompts_includes_seeded(client):
    # conftest seeds 3 prompt templates
    r = client.get("/api/prompts")
    assert r.status_code == 200
    assert len(r.json()) >= 3


def test_list_prompts_filter_by_type(client, db):
    _make_prompt(db, prompt_type="custom_type")
    r = client.get("/api/prompts?prompt_type=custom_type")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["prompt_type"] == "custom_type"


def test_list_prompts_filter_by_bucket_id(client, db):
    bucket_id = str(uuid.uuid4())
    _make_prompt(db, bucket_id=bucket_id)
    _make_prompt(db)  # no bucket
    r = client.get(f"/api/prompts?bucket_id={bucket_id}")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["bucket_id"] == bucket_id


def test_list_prompts_response_shape(client):
    data = client.get("/api/prompts").json()
    assert len(data) > 0
    for field in ("id", "prompt_type", "name", "content", "enabled", "version", "created_at"):
        assert field in data[0]


# ---------------------------------------------------------------------------
# POST /api/prompts
# ---------------------------------------------------------------------------

def test_create_prompt(client):
    payload = {
        "prompt_type": "description_generation",
        "name": "My Custom Prompt",
        "content": "Write a poetic description.",
        "enabled": True,
    }
    r = client.post("/api/prompts", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "My Custom Prompt"
    assert data["version"] == 1
    assert "id" in data


def test_create_prompt_with_bucket_id(client, db):
    bucket_id = str(uuid.uuid4())
    payload = {
        "prompt_type": "custom",
        "name": "Bucket Prompt",
        "content": "Classify this bucket.",
        "enabled": True,
        "bucket_id": bucket_id,
    }
    r = client.post("/api/prompts", json=payload)
    assert r.status_code == 200
    assert r.json()["bucket_id"] == bucket_id


def test_create_prompt_disabled(client):
    payload = {
        "prompt_type": "tags_generation",
        "name": "Disabled Prompt",
        "content": "Noop.",
        "enabled": False,
    }
    r = client.post("/api/prompts", json=payload)
    assert r.status_code == 200
    assert r.json()["enabled"] is False


# ---------------------------------------------------------------------------
# GET /api/prompts/{prompt_id}
# ---------------------------------------------------------------------------

def test_get_prompt(client, db):
    pt = _make_prompt(db)
    r = client.get(f"/api/prompts/{pt.id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == pt.id
    assert data["name"] == pt.name


def test_get_prompt_not_found(client):
    r = client.get("/api/prompts/nonexistent-id")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/prompts/{prompt_id}
# ---------------------------------------------------------------------------

def test_update_prompt_name(client, db):
    pt = _make_prompt(db)
    r = client.patch(f"/api/prompts/{pt.id}", json={"name": "Updated Name"})
    assert r.status_code == 200
    assert r.json()["name"] == "Updated Name"


def test_update_prompt_content_bumps_version(client, db):
    pt = _make_prompt(db)
    assert pt.version == 1
    r = client.patch(f"/api/prompts/{pt.id}", json={"content": "New content here."})
    assert r.status_code == 200
    assert r.json()["version"] == 2


def test_update_prompt_enabled(client, db):
    pt = _make_prompt(db, enabled=True)
    r = client.patch(f"/api/prompts/{pt.id}", json={"enabled": False})
    assert r.status_code == 200
    assert r.json()["enabled"] is False


def test_update_prompt_not_found(client):
    r = client.patch("/api/prompts/nonexistent", json={"name": "X"})
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# DELETE /api/prompts/{prompt_id}
# ---------------------------------------------------------------------------

def test_delete_prompt(client, db):
    pt = _make_prompt(db)
    r = client.delete(f"/api/prompts/{pt.id}")
    assert r.status_code == 200
    assert r.json()["deleted"] is True


def test_delete_prompt_removes_from_db(client, db):
    pt = _make_prompt(db)
    client.delete(f"/api/prompts/{pt.id}")
    r = client.get(f"/api/prompts/{pt.id}")
    assert r.status_code == 404


def test_delete_prompt_not_found(client):
    r = client.delete("/api/prompts/nonexistent")
    assert r.status_code == 404

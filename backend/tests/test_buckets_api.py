"""Test bucket CRUD API."""
import pytest


def test_list_buckets(client):
    resp = client.get("/api/buckets")
    assert resp.status_code == 200
    buckets = resp.json()
    assert len(buckets) >= 4
    names = [b["name"] for b in buckets]
    assert "Business" in names
    assert "Documents" in names
    assert "Personal" in names
    assert "Trash" in names


def test_create_bucket(client):
    resp = client.post("/api/buckets", json={
        "name": "TestBucket",
        "description": "For testing",
        "priority": 50,
        "mapping_mode": "virtual",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "TestBucket"
    assert data["id"] is not None


def test_create_duplicate_bucket_fails(client):
    resp = client.post("/api/buckets", json={"name": "Personal"})
    assert resp.status_code == 400


def test_update_bucket(client):
    resp = client.get("/api/buckets")
    bucket = next(b for b in resp.json() if b["name"] == "Personal")
    bid = bucket["id"]

    resp = client.patch(f"/api/buckets/{bid}", json={"description": "Updated description"})
    assert resp.status_code == 200
    assert resp.json()["description"] == "Updated description"


def test_delete_bucket(client):
    resp = client.post("/api/buckets", json={"name": "ToDelete", "priority": 999})
    assert resp.status_code == 200
    bid = resp.json()["id"]

    resp = client.delete(f"/api/buckets/{bid}")
    assert resp.status_code == 200

    resp = client.get(f"/api/buckets/{bid}")
    assert resp.status_code == 404


def test_bucket_has_confidence_threshold(client):
    resp = client.post("/api/buckets", json={
        "name": "HighConfBucket",
        "confidence_threshold": 0.9,
        "priority": 60,
    })
    assert resp.status_code == 200
    assert resp.json()["confidence_threshold"] == 0.9

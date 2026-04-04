"""
Tests for /api/audit-logs router.
"""
import uuid

import pytest

from app.models.audit_log import AuditLog


def _make_log(db, action="writeback_description", status="success",
              asset_id=None, job_run_id=None) -> AuditLog:
    log = AuditLog(
        id=str(uuid.uuid4()),
        asset_id=asset_id or str(uuid.uuid4()),
        job_run_id=job_run_id,
        action=action,
        status=status,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def test_list_audit_logs_empty(client):
    r = client.get("/api/audit-logs")
    assert r.status_code == 200
    assert r.json() == []


def test_list_audit_logs(client, db):
    _make_log(db)
    _make_log(db, action="writeback_tags")
    r = client.get("/api/audit-logs")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_list_audit_logs_filter_status(client, db):
    _make_log(db, status="success")
    _make_log(db, status="failed")
    r = client.get("/api/audit-logs?status=success")
    assert r.status_code == 200
    assert all(l["status"] == "success" for l in r.json())


def test_list_audit_logs_filter_action(client, db):
    _make_log(db, action="writeback_tags")
    _make_log(db, action="writeback_description")
    r = client.get("/api/audit-logs?action=writeback_tags")
    assert r.status_code == 200
    assert all(l["action"] == "writeback_tags" for l in r.json())


def test_list_audit_logs_filter_asset_id(client, db):
    asset_id = str(uuid.uuid4())
    _make_log(db, asset_id=asset_id)
    _make_log(db)
    r = client.get(f"/api/audit-logs?asset_id={asset_id}")
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["asset_id"] == asset_id


def test_list_audit_logs_filter_job_run_id(client, db):
    job_id = str(uuid.uuid4())
    _make_log(db, job_run_id=job_id)
    _make_log(db)
    r = client.get(f"/api/audit-logs?job_run_id={job_id}")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_audit_log_count(client, db):
    _make_log(db, status="success")
    _make_log(db, status="success")
    _make_log(db, status="failed")
    r = client.get("/api/audit-logs/count?status=success")
    assert r.status_code == 200
    assert r.json()["count"] == 2


def test_get_audit_log(client, db):
    log = _make_log(db)
    r = client.get(f"/api/audit-logs/{log.id}")
    assert r.status_code == 200
    assert r.json()["id"] == log.id
    assert r.json()["action"] == log.action


def test_get_audit_log_not_found(client):
    r = client.get("/api/audit-logs/nonexistent")
    assert r.status_code == 404


def test_audit_log_pagination(client, db):
    for _ in range(5):
        _make_log(db)
    r = client.get("/api/audit-logs?page=1&page_size=2")
    assert r.status_code == 200
    assert len(r.json()) == 2

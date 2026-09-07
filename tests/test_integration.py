"""HR ↔ 综合系统 3.0 integration APIs + KPI V2.2 breakdown."""
from datetime import date

from tests.test_permissions import _add_passed_trainings, _create_dept_pos_emp


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_integration_requires_auth(client):
    r = client.get("/api/v1/integration/sync/status")
    assert r.status_code == 401


def test_sync_status_with_api_key(client, auth_headers):
    r = client.get("/api/v1/integration/sync/status", headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "counts" in body
    assert "last_syncs" in body
    assert "sys_users" in body["counts"]
    assert "pending_revokes" in body["counts"]


def test_sync_users_upsert_and_link(client, auth_headers):
    emp_id = _create_dept_pos_emp(client, auth_headers, emp_no="E-SYNC1")
    r = client.post(
        "/api/v1/integration/sync/users",
        json={
            "users": [
                {
                    "id": "sys3-E-SYNC1",
                    "username": "sync.user1",
                    "display_name": "同步用户一",
                    "dept_code": "D-E-SYNC1",
                    "status": "active",
                }
            ]
        },
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is True
    assert body["created"] == 1
    assert body["linked"] == 1
    assert body["items"][0]["employee_id"] == emp_id
    assert body["items"][0]["system_account_id"] == "sys3-E-SYNC1"

    emp = client.get(f"/api/v1/employees/{emp_id}", headers=auth_headers)
    assert emp.status_code == 200
    assert emp.json()["system_account_id"] == "sys3-E-SYNC1"
    assert emp.json()["sys_user_id"] is not None


def test_validate_training_fail_and_pass(client, auth_headers):
    emp_id = _create_dept_pos_emp(client, auth_headers, emp_no="E-VAL-FAIL")
    r = client.post(
        "/api/v1/integration/validate-training-before-grant",
        json={"employee_id": emp_id, "scopes": ["wipe", "outbound"]},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ok"] is False
    assert body["gate_applied"] is True
    assert set(body["missing_courses"]) == {"safety", "sop", "wipe_r2"}

    emp2 = _create_dept_pos_emp(client, auth_headers, emp_no="E-VAL-OK")
    _add_passed_trainings(client, auth_headers, emp2)
    r2 = client.post(
        "/api/v1/integration/validate-training-before-grant",
        json={"system_account_id": "sys3-E-VAL-OK", "scopes": ["wipe"]},
        headers=auth_headers,
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["ok"] is True
    assert r2.json()["missing_courses"] == []


def test_validate_training_no_gate_for_nonsensitive(client, auth_headers):
    emp_id = _create_dept_pos_emp(
        client, auth_headers, is_media=False, is_critical=False, emp_no="E-VAL-NS"
    )
    r = client.post(
        "/api/v1/integration/validate-training-before-grant",
        json={"employee_id": emp_id, "scopes": ["read"]},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert r.json()["gate_applied"] is False


def test_pending_revokes_and_permission_callback(client, auth_headers):
    emp_id = _create_dept_pos_emp(
        client, auth_headers, is_media=False, is_critical=True, emp_no="E-LEAVE"
    )
    patch = client.patch(
        f"/api/v1/employees/{emp_id}",
        json={"status": "leave", "leave_date": date.today().isoformat()},
        headers=auth_headers,
    )
    assert patch.status_code == 200, patch.text

    pending = client.get("/api/v1/integration/pending-revokes", headers=auth_headers)
    assert pending.status_code == 200, pending.text
    rows = pending.json()
    assert any(x["employee_id"] == emp_id and x["reason"] == "leave" for x in rows)

    rev = client.post(
        "/api/v1/permissions/revoke",
        json={
            "employee_id": emp_id,
            "scopes": ["wipe", "outbound"],
            "trigger": "leave",
            "reason": "离职回收",
        },
        headers=auth_headers,
    )
    assert rev.status_code == 200
    assert rev.json()["status"] == "pending"
    event_id = rev.json()["id"]

    cb = client.post(
        "/api/v1/integration/permission-callback",
        json={
            "system_account_id": "sys3-E-LEAVE",
            "event_type": "revoke",
            "scopes": ["wipe", "outbound"],
            "status": "done",
            "trigger": "leave",
            "operator": "sys3-demo",
            "external_ref": "RV-DEMO-1",
        },
        headers=auth_headers,
    )
    assert cb.status_code == 200, cb.text
    assert cb.json()["id"] == event_id
    assert cb.json()["status"] == "done"
    assert cb.json()["completed_at"] is not None

    pending2 = client.get("/api/v1/integration/pending-revokes", headers=auth_headers)
    assert not any(x["employee_id"] == emp_id for x in pending2.json())


def test_kpi_v22_breakdown_weights(client, auth_headers):
    r = client.post("/api/v1/kpi/batch/2026-09/run", headers=auth_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scheme"] == "V2.2"
    assert body["max_score"] == 100.0
    codes = [s["kpi_code"] for s in body["scores"]]
    assert codes == [
        "3.1",
        "3.2",
        "3.3",
        "3.4",
        "3.5",
        "3.6",
        "3.7",
        "3.8",
        "3.9",
        "3.10",
        "3.11",
        "3.12",
        "3.13",
    ]
    weights = {s["kpi_code"]: s["weight"] for s in body["scores"]}
    assert weights["3.1"] == 12
    assert weights["3.2"] == 6
    assert weights["3.3"] == 4
    assert weights["3.4"] == 10
    assert weights["3.5"] == 8
    assert weights["3.6"] == 8
    assert weights["3.7"] == 10
    assert weights["3.8"] == 8
    assert weights["3.9"] == 6
    assert weights["3.10"] == 12
    assert weights["3.11"] == 6
    assert weights["3.12"] == 5
    assert weights["3.13"] == 5
    assert abs(sum(weights.values()) - 100) < 1e-6
    for s in body["scores"]:
        assert "score" in s and "weighted_score" in s and "detail" in s

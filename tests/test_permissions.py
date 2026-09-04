"""Training gate + revoke T+0 tests."""
from datetime import date, timedelta


def _create_dept_pos_emp(client, headers, *, is_media=True, is_critical=True, emp_no="E9"):
    d = client.post("/api/v1/departments", json={"code": f"D-{emp_no}", "name": "测试部"}, headers=headers)
    assert d.status_code == 200, d.text
    dept_id = d.json()["id"]
    p = client.post(
        "/api/v1/positions",
        json={"code": f"P-{emp_no}", "title": "测试岗", "dept_id": dept_id},
        headers=headers,
    )
    assert p.status_code == 200, p.text
    e = client.post(
        "/api/v1/employees",
        json={
            "emp_no": emp_no,
            "name": "测试员",
            "dept_id": dept_id,
            "position_id": p.json()["id"],
            "is_media_contact": is_media,
            "is_critical_role": is_critical,
            "system_account_id": f"sys3-{emp_no}",
        },
        headers=headers,
    )
    assert e.status_code == 200, e.text
    return e.json()["id"]


def _add_passed_trainings(client, headers, emp_id):
    valid = (date.today() + timedelta(days=90)).isoformat()
    for code, name in [("safety", "安全"), ("sop", "SOP"), ("wipe_r2", "擦除R2")]:
        r = client.post(
            "/api/v1/trainings",
            json={
                "employee_id": emp_id,
                "course_code": code,
                "course_name": name,
                "status": "passed",
                "score": 90,
                "trained_at": date.today().isoformat(),
                "valid_until": valid,
            },
            headers=headers,
        )
        assert r.status_code == 200, r.text


def test_grant_without_training_fails(client, auth_headers):
    emp_id = _create_dept_pos_emp(client, auth_headers, emp_no="E-NO-TRAIN")
    r = client.post(
        "/api/v1/permissions/grant",
        json={"employee_id": emp_id, "scopes": ["wipe", "read"], "reason": "demo"},
        headers=auth_headers,
    )
    assert r.status_code == 403
    assert "培训" in r.json()["detail"]


def test_grant_with_training_succeeds(client, auth_headers):
    emp_id = _create_dept_pos_emp(client, auth_headers, emp_no="E-TRAINED")
    _add_passed_trainings(client, auth_headers, emp_id)
    r = client.post(
        "/api/v1/permissions/grant",
        json={"employee_id": emp_id, "scopes": ["wipe", "outbound"], "operator": "tester"},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["event_type"] == "grant"
    assert "wipe" in body["scopes"]


def test_revoke_critical_leave_due_t0(client, auth_headers):
    emp_id = _create_dept_pos_emp(
        client, auth_headers, is_media=False, is_critical=True, emp_no="E-CRIT"
    )
    r = client.post(
        "/api/v1/permissions/revoke",
        json={
            "employee_id": emp_id,
            "scopes": ["wipe", "outbound"],
            "trigger": "leave",
            "reason": "离职回收",
        },
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["event_type"] == "revoke"
    assert body["due_at"] is not None
    assert body["status"] == "pending"


def test_revoke_normal_not_pending(client, auth_headers):
    emp_id = _create_dept_pos_emp(
        client, auth_headers, is_media=False, is_critical=False, emp_no="E-NORM"
    )
    r = client.post(
        "/api/v1/permissions/revoke",
        json={"employee_id": emp_id, "scopes": ["read"], "trigger": "normal"},
        headers=auth_headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "done"
    assert r.json()["due_at"] is None

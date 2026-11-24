"""Notification outbox and safety-escalation notifications. Synthetic data; memory provider only."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import notifications, safety_escalations
from app.main import app

client = TestClient(app, raise_server_exceptions=False)
OWNER, OPENER, ONCALL, ADMIN = "clin-nt-owner", "rev-nt-opener", "clin-nt-oncall", "admin-nt"


@pytest.fixture
def memory(monkeypatch):
    monkeypatch.setenv("STN_NOTIFY_PROVIDER", "memory")
    p = notifications.memory_provider()
    p.sent.clear()
    p.fail_next.clear()
    return p


def new_client(act, code="SYN-NT"):
    act(OWNER, "clinician")
    return client.post("/v1/clients", json={"display_code": code}).json()["id"]


def open_escalation(act, cid, who=OPENER, role="reviewer", severity="urgent_assessment"):
    act(who, role)
    return client.post("/v1/safety-escalations", json={"client_id": cid, "source": "clinician_report", "severity": severity})


def outbox(raw):
    return raw("SELECT recipient_sub, template_id, status, attempts, last_error_code FROM notification_outbox ORDER BY recipient_sub")


def test_opening_notifies_owner_and_roster_but_not_the_opener(backend, act, memory, raw, monkeypatch):
    monkeypatch.setenv("STN_SAFETY_NOTIFY_SUBJECTS", f"{ONCALL},{OPENER}")
    cid = new_client(act)
    r = open_escalation(act, cid)
    assert r.status_code == 201 and r.json()["notified"] == 2
    assert [(x[0], x[2]) for x in outbox(raw)] == sorted([(OWNER, "pending"), (ONCALL, "pending")])
    assert notifications.dispatch_due() == {"sent": 2, "retry": 0, "dead": 0, "not_configured": 0}
    msg = memory.sent[0]
    assert "urgent" in msg["subject"] and r.json()["id"] in msg["body"]
    assert cid not in msg["subject"] + msg["body"] and "SYN-NT" not in msg["subject"] + msg["body"]  # no client identity
    assert [x[2] for x in outbox(raw)] == ["sent", "sent"]
    assert notifications.dispatch_due()["sent"] == 0  # nothing is sent twice


def test_provider_outage_never_blocks_or_loses_an_escalation(backend, act, memory, raw):
    cid = new_client(act)
    memory.fail_next[:] = [notifications.TransientSendError] * notifications.MAX_ATTEMPTS
    eid = open_escalation(act, cid).json()["id"]
    now = datetime.now(timezone.utc)
    for i in range(notifications.MAX_ATTEMPTS):
        counts = notifications.dispatch_due(now=now + timedelta(days=i + 1))
        assert counts["retry" if i < notifications.MAX_ATTEMPTS - 1 else "dead"] == 1
    assert outbox(raw)[0][2:] == ("dead", notifications.MAX_ATTEMPTS, "retries_exhausted")
    act(OWNER, "clinician")
    assert client.get(f"/v1/safety-escalations/{eid}").json()["status"] == "open"  # escalation unaffected
    act(ADMIN, "admin")
    dead = client.get("/v1/admin/notifications?status=dead").json()
    assert len(dead["notifications"]) == 1 and "params_json" not in dead["notifications"][0]


def test_retry_backoff_then_success_and_permanent_failure(backend, act, memory, raw):
    cid = new_client(act)
    memory.fail_next[:] = [notifications.TransientSendError]
    open_escalation(act, cid)
    now = datetime.now(timezone.utc)
    assert notifications.dispatch_due(now=now)["retry"] == 1
    assert notifications.dispatch_due(now=now + timedelta(seconds=30))["sent"] == 0  # not yet due
    assert notifications.dispatch_due(now=now + timedelta(minutes=2))["sent"] == 1
    other = new_client(act, "SYN-NT2")
    memory.fail_next[:] = [notifications.PermanentSendError]
    open_escalation(act, other)
    assert notifications.dispatch_due(now=now + timedelta(minutes=3))["dead"] == 1


def test_disabled_provider_fails_closed(backend, act, raw, monkeypatch):
    monkeypatch.delenv("STN_NOTIFY_PROVIDER", raising=False)
    cid = new_client(act)
    assert open_escalation(act, cid).status_code == 201
    assert notifications.dispatch_due()["not_configured"] == 1
    assert outbox(raw)[0][2] == "pending"
    act(ADMIN, "admin")
    assert "disabled" in client.get("/v1/admin/notifications").json()["provider"]
    from app import db
    monkeypatch.setenv(db.ENVIRONMENT_ENV, "production")
    monkeypatch.setenv("STN_NOTIFY_PROVIDER", "memory")
    with pytest.raises(notifications.ProviderNotConfigured):
        notifications.provider()
    monkeypatch.setenv("STN_NOTIFY_PROVIDER", "acs")
    with pytest.raises(notifications.ProviderNotConfigured):
        notifications.provider()


def test_database_failure_rolls_back_escalation_and_notification_together(backend, act, memory, raw, monkeypatch):
    cid = new_client(act)

    def broken(*args, **kwargs):
        raise RuntimeError("simulated database failure while queuing")

    monkeypatch.setattr(notifications, "enqueue", broken)
    assert open_escalation(act, cid).status_code == 500
    assert raw("SELECT COUNT(*) FROM safety_escalations")[0][0] == 0
    assert raw("SELECT COUNT(*) FROM notification_outbox")[0][0] == 0


def test_duplicates_are_prevented(backend, act, memory, raw):
    cid = new_client(act)
    eid = open_escalation(act, cid).json()["id"]
    from app import db
    with db.transaction() as conn:
        again = notifications.enqueue(conn, "org-synthetic-1", "safety_escalation_opened", [OWNER, OWNER],
                                      {"priority": "urgent", "reference": eid}, f"esc:{eid}:opened")
    assert again == 0 and len(outbox(raw)) == 1


def test_overdue_notice_is_sent_once(backend, act, memory, raw, monkeypatch):
    cid = new_client(act)
    open_escalation(act, cid, severity="immediate_emergency")
    later = datetime.now(timezone.utc) + timedelta(minutes=30)
    assert safety_escalations.queue_overdue_notifications(now=later) == 1
    assert safety_escalations.queue_overdue_notifications(now=later) == 0
    assert [x[1] for x in outbox(raw)].count("safety_escalation_overdue") == 1
    assert safety_escalations.queue_overdue_notifications(now=datetime.now(timezone.utc)) == 0


def test_preferences_cannot_silence_safety_or_security(backend, act, memory, raw):
    act(OWNER, "clinician")
    r = client.post("/v1/me/notification-preferences", json={"category": "safety_escalation", "opted_out": True})
    assert r.status_code == 422
    assert client.post("/v1/me/notification-preferences", json={"category": "security", "opted_out": True}).status_code == 422
    assert client.post("/v1/me/notification-preferences", json={"category": "follow_up_reminder", "opted_out": True}).status_code == 200
    assert client.post("/v1/me/notification-preferences", json={"category": "nonsense", "opted_out": True}).status_code == 422
    cid = new_client(act)
    open_escalation(act, cid)
    assert outbox(raw)[0][2] == "pending"  # still delivered


def test_free_text_and_unknown_params_are_refused(backend):
    from app import db
    with db.transaction() as conn:
        with pytest.raises(ValueError):
            notifications.enqueue(conn, "o", "safety_escalation_opened", ["x"],
                                  {"priority": "urgent", "reference": "Client Jane Doe self-harm"}, "k1")
        with pytest.raises(ValueError):
            notifications.enqueue(conn, "o", "safety_escalation_opened", ["x"], {"priority": "urgent"}, "k2")


def test_outbox_is_admin_only_and_org_scoped(backend, act, memory, raw):
    cid = new_client(act)
    open_escalation(act, cid)
    act(OWNER, "clinician")
    assert client.get("/v1/admin/notifications").status_code == 403
    act("admin-other-org", "admin", org="org-synthetic-2")
    assert client.get("/v1/admin/notifications").json()["notifications"] == []
    with pytest.raises(Exception):
        raw("DELETE FROM notification_outbox")

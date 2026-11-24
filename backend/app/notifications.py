"""Notification service: transactional outbox, provider abstraction, retries, dedupe, preferences.

How it works
- enqueue(conn, ...) is called inside the same database transaction as the event (an escalation
  opened, an invitation issued...). The event and its notification commit or roll back together;
  a provider outage can never lose or block the event itself.
- dispatch_due() sends pending rows through the configured provider, with exponential backoff
  (RETRY_MINUTES) and a dead-letter state after MAX_ATTEMPTS. Run it from a scheduled job:
  `python -m app.notifications --dispatch`. It is not scheduled anywhere yet.
- Duplicates: (org, dedupe_key, recipient) is unique; enqueueing the same event twice is a no-op.
- Preferences: a subject may opt out of a category, except MANDATORY categories (safety,
  security), which are always delivered. An opted-out row is recorded as 'suppressed'.
- Content: templates carry no clinical information and no client identity: a generic prompt to
  sign in, a priority label and an opaque reference. Recipients are token subjects; the provider
  adapter resolves the delivery address from the identity directory at send time.

Providers (STN_NOTIFY_PROVIDER)
- "disabled" (default): nothing is sent; rows stay pending and the admin view says so. Fail closed.
- "memory": records messages in process memory. Tests and local demos only; refused when
  STN_ENVIRONMENT is staging or production.
- "acs": Azure Communication Services email. NOT IMPLEMENTED: needs an approved provider, a verified
  sender domain (SPF, DKIM, DMARC) and owner approval before any real message is sent.

Nothing here tells anyone that a message was read or acted on. A 'sent' status means the provider
accepted it, nothing more.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from . import audit, db

CATEGORIES = frozenset({
    "registration", "verification", "assessment_invitation", "assessment_completed", "appointment_reminder",
    "clinician_assignment", "follow_up_reminder", "administrative", "safety_escalation", "security",
})
MANDATORY = frozenset({"safety_escalation", "security"})
RETRY_MINUTES = (1, 5, 15, 60, 240)
MAX_ATTEMPTS = len(RETRY_MINUTES) + 1
PROVIDER_ENV = "STN_NOTIFY_PROVIDER"
_KEY = re.compile(r"^[A-Za-z0-9_.:-]{1,200}$")
_PARAM_VALUE = re.compile(r"^[A-Za-z0-9_.:-]{0,128}$")


@dataclass(frozen=True)
class Template:
    template_id: str
    version: str
    category: str
    subject: str
    body: str
    params: tuple[str, ...]


TEMPLATES: dict[str, Template] = {t.template_id: t for t in (
    Template("safety_escalation_opened", "1", "safety_escalation",
             "STN: {priority} item needs attention in the clinician workspace",
             "An item that needs clinical attention has been recorded. Sign in to the STN clinician workspace "
             "to view it. Reference: {reference}.\n\nThis message contains no client information. If you "
             "cannot act on it, hand it over in the workspace.",
             ("priority", "reference")),
    Template("safety_escalation_overdue", "1", "safety_escalation",
             "STN: {priority} item not yet acknowledged",
             "An item that needs clinical attention has not been acknowledged within its time window. Sign in "
             "to the STN clinician workspace. Reference: {reference}.",
             ("priority", "reference")),
    Template("client_invitation", "1", "registration",
             "Your invitation to Supportive Therapy Network",
             "Your clinician has invited you to create an STN account. Use the code they gave you when you "
             "sign in. If you did not expect this, ignore this message.",
             ()),
    Template("security_notice", "1", "security",
             "STN: security notice for your account",
             "There has been a security-relevant change to your STN account ({event}). If this was not you, "
             "contact STN.",
             ("event",)),
)}


class NotificationError(Exception):
    pass


class TransientSendError(NotificationError):
    """Retry later (timeouts, throttling, 5xx)."""


class PermanentSendError(NotificationError):
    """Do not retry (rejected recipient, invalid template)."""


class ProviderNotConfigured(NotificationError):
    pass


def render(template_id: str, params: dict[str, str]) -> tuple[str, str]:
    t = TEMPLATES[template_id]
    return t.subject.format(**params), t.body.format(**params)


# --------------------------------------------------------------------------- providers


class MemoryProvider:
    """Test/local provider. fail_next lets tests simulate transient or permanent failures."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self.fail_next: list[type[Exception]] = []

    def send(self, recipient_sub: str, subject: str, body: str) -> str:
        if self.fail_next:
            raise self.fail_next.pop(0)("simulated provider failure")
        message_id = "mem-" + uuid.uuid4().hex
        self.sent.append({"to": recipient_sub, "subject": subject, "body": body, "id": message_id})
        return message_id


_memory = MemoryProvider()


def memory_provider() -> MemoryProvider:
    return _memory


def provider() -> Any:
    name = os.getenv(PROVIDER_ENV, "disabled").strip().lower() or "disabled"
    if name == "disabled":
        raise ProviderNotConfigured("No notification provider is configured (STN_NOTIFY_PROVIDER=disabled).")
    if name == "memory":
        if db.hosted_environment():
            raise ProviderNotConfigured("The memory provider is not allowed in staging or production.")
        return _memory
    raise ProviderNotConfigured(f"Notification provider '{name}' is not implemented or not approved.")


# --------------------------------------------------------------------------- enqueue


def _opted_out(conn: db.Conn, org: str, subject: str, category: str) -> bool:
    if category in MANDATORY:
        return False
    row = conn.execute(
        "SELECT opted_out FROM notification_preferences WHERE org_id = ? AND subject = ? AND category = ?",
        (org, subject, category),
    ).fetchone()
    return bool(row and row["opted_out"])


def enqueue(conn: db.Conn, org: str, template_id: str, recipients: list[str], params: dict[str, str],
            dedupe_key: str) -> int:
    """Queue one message per recipient inside the caller's transaction. Returns how many were new."""
    t = TEMPLATES[template_id]
    if set(params) != set(t.params):
        raise ValueError(f"Template {template_id} needs params {t.params}.")
    if any(not isinstance(v, str) or not _PARAM_VALUE.match(v) for v in params.values()):
        raise ValueError("Notification parameters must be identifiers or codes, never free text.")
    if not _KEY.match(dedupe_key):
        raise ValueError("Invalid dedupe key.")
    created = 0
    stamp = audit.now()
    for recipient in dict.fromkeys(r for r in recipients if r):
        exists = conn.execute(
            "SELECT 1 AS x FROM notification_outbox WHERE org_id = ? AND dedupe_key = ? AND recipient_sub = ?",
            (org, dedupe_key, recipient),
        ).fetchone()
        if exists:
            continue
        status = "suppressed" if _opted_out(conn, org, recipient, t.category) else "pending"
        nid = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO notification_outbox (id, org_id, category, template_id, template_version, recipient_sub, "
            "params_json, dedupe_key, status, attempts, next_attempt_at, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
            (nid, org, t.category, t.template_id, t.version, recipient, json.dumps(params, sort_keys=True),
             dedupe_key, status, stamp, stamp),
        )
        audit.append(conn, "system:notifications", f"notification.queue.{t.template_id}", "notification", nid,
                     "ok" if status == "pending" else "suppressed_opt_out", org=org)
        created += 1
    return created


# --------------------------------------------------------------------------- dispatch


def dispatch_due(limit: int = 50, now: datetime | None = None) -> dict[str, int]:
    """Send due messages. Each message is handled in its own transaction."""
    now = now or datetime.now(timezone.utc)
    counts = {"sent": 0, "retry": 0, "dead": 0, "not_configured": 0}
    try:
        sender = provider()
    except ProviderNotConfigured:
        counts["not_configured"] = 1
        return counts
    with db.transaction() as conn:
        due = [r["id"] for r in conn.execute(
            "SELECT id FROM notification_outbox WHERE status = 'pending' AND next_attempt_at <= ? "
            "ORDER BY next_attempt_at, id LIMIT ?", (now.isoformat(), int(limit))).fetchall()]
    for nid in due:
        with db.transaction() as conn:
            if conn.kind == "postgres":
                row = conn.execute("SELECT * FROM notification_outbox WHERE id = ? AND status = 'pending' "
                                   "FOR UPDATE SKIP LOCKED", (nid,)).fetchone()
            else:
                row = conn.execute("SELECT * FROM notification_outbox WHERE id = ? AND status = 'pending'",
                                   (nid,)).fetchone()
            if row is None:
                continue
            subject, body = render(row["template_id"], json.loads(row["params_json"]))
            attempts = row["attempts"] + 1
            try:
                message_id = sender.send(row["recipient_sub"], subject, body)
            except PermanentSendError:
                outcome, status, code, nxt = "dead_permanent", "dead", "permanent", row["next_attempt_at"]
            except Exception:  # transient, including timeouts and unexpected provider errors
                if attempts >= MAX_ATTEMPTS:
                    outcome, status, code, nxt = "dead_retries_exhausted", "dead", "retries_exhausted", row["next_attempt_at"]
                else:
                    outcome, status, code = "retry", "pending", "transient"
                    nxt = (now + timedelta(minutes=RETRY_MINUTES[attempts - 1])).isoformat()
            else:
                conn.execute(
                    "UPDATE notification_outbox SET status = 'sent', attempts = ?, sent_at = ?, provider_message_id = ?, "
                    "last_error_code = NULL WHERE id = ? AND status = 'pending'",
                    (attempts, now.isoformat(), message_id, nid))
                audit.append(conn, "system:notifications", "notification.send", "notification", nid, "ok", org=row["org_id"])
                counts["sent"] += 1
                continue
            conn.execute(
                "UPDATE notification_outbox SET status = ?, attempts = ?, next_attempt_at = ?, last_error_code = ? "
                "WHERE id = ? AND status = 'pending'", (status, attempts, nxt, code, nid))
            audit.append(conn, "system:notifications", "notification.send", "notification", nid, outcome, org=row["org_id"])
            counts["dead" if status == "dead" else "retry"] += 1
    return counts


# --------------------------------------------------------------------------- admin and preferences


def list_for_admin(actor: str, org: str, status: str | None = None, limit: int = 200) -> dict[str, Any]:
    """Metadata only: no rendered content, no parameters."""
    sql = ("SELECT id, category, template_id, template_version, recipient_sub, status, attempts, next_attempt_at, "
           "last_error_code, created_at, sent_at FROM notification_outbox WHERE org_id = ?")
    args: list[Any] = [org]
    if status:
        sql += " AND status = ?"
        args.append(status)
    sql += " ORDER BY created_at DESC, id LIMIT ?"
    args.append(int(limit))
    try:
        provider()
        provider_state = "configured"
    except ProviderNotConfigured as exc:
        provider_state = str(exc)
    with db.transaction() as conn:
        rows = conn.execute(sql, tuple(args)).fetchall()
        audit.append(conn, actor, "notification.list", "notification", None, "ok", org=org)
    return {"provider": provider_state, "notifications": rows}


def set_preference(subject: str, org: str, category: Any, opted_out: Any) -> dict[str, Any]:
    if category not in CATEGORIES:
        raise ValueError("Unknown notification category.")
    if category in MANDATORY:
        raise ValueError("Safety and security notifications cannot be turned off.")
    if not isinstance(opted_out, bool):
        raise ValueError("opted_out must be true or false.")
    with db.transaction() as conn:
        if conn.kind == "postgres":
            conn.execute(
                "INSERT INTO notification_preferences (org_id, subject, category, opted_out, updated_at) "
                "VALUES (?, ?, ?, ?, ?) ON CONFLICT (org_id, subject, category) DO UPDATE SET "
                "opted_out = EXCLUDED.opted_out, updated_at = EXCLUDED.updated_at",
                (org, subject, category, int(opted_out), audit.now()))
        else:
            conn.execute(
                "INSERT OR REPLACE INTO notification_preferences (org_id, subject, category, opted_out, updated_at) "
                "VALUES (?, ?, ?, ?, ?)", (org, subject, category, int(opted_out), audit.now()))
        audit.append(conn, subject, f"notification.preference.{category}", "subject", subject,
                     "opt_out" if opted_out else "opt_in", org=org)
    return {"category": category, "opted_out": opted_out}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.notifications")
    parser.add_argument("--dispatch", action="store_true", help="send due notifications once")
    parser.add_argument("--scan-overdue", action="store_true", help="queue overdue safety-escalation notices")
    parser.add_argument("--limit", type=int, default=50)
    args = parser.parse_args(argv)
    if args.scan_overdue:
        from . import safety_escalations
        print(json.dumps({"overdue_queued": safety_escalations.queue_overdue_notifications()}))
    if args.dispatch:
        print(json.dumps(dispatch_due(args.limit)))
    return 0


if __name__ == "__main__":
    sys.exit(main())

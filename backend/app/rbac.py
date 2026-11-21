"""Server-side role-based access control.

Roles are read from the database on every request. They are never taken from the
token or from client-supplied data. Every grant, revoke and denial is audited.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from . import audit, store
from .auth import require_identity


class Role(str, Enum):
    PLATFORM_ADMINISTRATOR = "platform_administrator"
    ORGANISATION_ADMINISTRATOR = "organisation_administrator"
    CLINICAL_DIRECTOR = "clinical_director"
    AUTHORISED_CLINICIAN = "authorised_clinician"
    CLINICAL_SUPERVISOR = "clinical_supervisor"
    INTAKE_COORDINATOR = "intake_coordinator"
    CUSTOMER = "customer"
    AUDITOR = "auditor"


PERMISSIONS: dict[Role, frozenset[str]] = {
    Role.PLATFORM_ADMINISTRATOR: frozenset({"platform:configure", "rbac:grant", "audit:read"}),
    Role.ORGANISATION_ADMINISTRATOR: frozenset({"org:manage"}),
    Role.CLINICAL_DIRECTOR: frozenset({"clinical:governance", "audit:read"}),
    Role.AUTHORISED_CLINICIAN: frozenset({"client:create", "clinical:read_assigned", "clinical:write_assigned"}),
    Role.CLINICAL_SUPERVISOR: frozenset({"clinical:oversight"}),
    Role.INTAKE_COORDINATOR: frozenset({"intake:manage"}),
    Role.CUSTOMER: frozenset({"customer:read_own", "customer:update_own"}),
    Role.AUDITOR: frozenset({"audit:read"}),
}

ALL_PERMISSIONS = frozenset().union(*PERMISSIONS.values())


class PermissionDenied(PermissionError):
    """Raised when an actor lacks the permission for an administrative action."""


def permissions_for(roles: Iterable[Role]) -> frozenset[str]:
    granted: set[str] = set()
    for role in roles:
        granted |= PERMISSIONS[role]
    return frozenset(granted)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def roles_for(conn: sqlite3.Connection, subject: str) -> frozenset[Role]:
    rows = conn.execute(
        "SELECT role FROM role_assignments WHERE subject = ? AND revoked_at IS NULL", (subject,)
    ).fetchall()
    return frozenset(Role(r["role"]) for r in rows)


def _grant_in_tx(conn: sqlite3.Connection, actor: str, subject: str, role: Role) -> bool:
    active = conn.execute(
        "SELECT 1 FROM role_assignments WHERE subject = ? AND role = ? AND revoked_at IS NULL",
        (subject, role.value),
    ).fetchone()
    if active:
        return False
    conn.execute(
        "INSERT INTO role_assignments (subject, role, granted_by, granted_at) VALUES (?, ?, ?, ?)",
        (subject, role.value, actor, _now()),
    )
    audit.append_in_tx(conn, actor, "rbac.grant", f"subject:{subject}", {"role": role.value})
    return True


def _run_in_tx(fn):
    with store._connect() as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            result = fn(conn)
            conn.execute("COMMIT")
            return result
        except Exception:
            if conn.in_transaction:
                conn.execute("ROLLBACK")
            raise


def grant_role(actor: str, subject: str, role: Role) -> bool:
    role = Role(role)

    def _do(conn):
        if "rbac:grant" not in permissions_for(roles_for(conn, actor)):
            audit.append_in_tx(conn, actor, "rbac.denied", f"subject:{subject}", {"role": role.value})
            conn.execute("COMMIT")
            raise PermissionDenied("Not permitted to grant roles.")
        return _grant_in_tx(conn, actor, subject, role)

    return _run_in_tx(_do)


def grant_system_role(subject: str, role: Role) -> bool:
    """Internal use only, by platform services such as onboarding. Not exposed as a route."""
    return _run_in_tx(lambda conn: _grant_in_tx(conn, "system", subject, Role(role)))


def revoke_role(actor: str, subject: str, role: Role) -> bool:
    role = Role(role)

    def _do(conn):
        if "rbac:grant" not in permissions_for(roles_for(conn, actor)):
            audit.append_in_tx(conn, actor, "rbac.denied", f"subject:{subject}", {"role": role.value})
            conn.execute("COMMIT")
            raise PermissionDenied("Not permitted to revoke roles.")
        cur = conn.execute(
            "UPDATE role_assignments SET revoked_at = ? WHERE subject = ? AND role = ? AND revoked_at IS NULL",
            (_now(), subject, role.value),
        )
        if cur.rowcount:
            audit.append_in_tx(conn, actor, "rbac.revoke", f"subject:{subject}", {"role": role.value})
        return bool(cur.rowcount)

    return _run_in_tx(_do)


def require_permission(permission: str):
    if permission not in ALL_PERMISSIONS:
        raise ValueError(f"Unknown permission: {permission}")

    def _dependency(identity: dict = Depends(require_identity)) -> dict:
        try:
            with store._connect() as conn:
                granted = permissions_for(roles_for(conn, identity["sub"]))
                if permission in granted:
                    return identity
                conn.execute("BEGIN IMMEDIATE")
                audit.append_in_tx(conn, identity["sub"], "access.denied", f"permission:{permission}", {})
                conn.execute("COMMIT")
        except store.StoreNotConfigured as exc:
            raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Access control is not available.") from exc
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted.")

    return _dependency


router = APIRouter(prefix="/v1/admin", tags=["administration"])


class RoleGrant(BaseModel):
    subject: str
    role: Role


@router.post("/roles", status_code=status.HTTP_201_CREATED)
def grant_role_route(body: RoleGrant, identity: dict = Depends(require_permission("rbac:grant"))) -> dict:
    try:
        created = grant_role(identity["sub"], body.subject, body.role)
    except PermissionDenied as exc:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not permitted.") from exc
    except store.StoreNotConfigured as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Access control is not available.") from exc
    return {"subject": body.subject, "role": body.role.value, "granted": created}

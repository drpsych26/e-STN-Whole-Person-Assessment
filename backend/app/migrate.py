"""Apply database migrations as a separate step, and grant the API's runtime role.

    python -m app.migrate [--status] [--grant-runtime-role NAME] [--create-entra-principal]
                          [--bootstrap-admin-org ORG --bootstrap-admin-subject SUBJECT]

Environment equivalents (used by the container's migration role):
    STN_DB_RUNTIME_ROLE=<name>              same as --grant-runtime-role
    STN_DB_CREATE_ENTRA_PRINCIPAL=true      same as --create-entra-principal
    STN_BOOTSTRAP_ADMIN_ORG=<org>           same as --bootstrap-admin-org
    STN_BOOTSTRAP_ADMIN_SUBJECT=<subject>   same as --bootstrap-admin-subject

Applies every pending migration (idempotent; PostgreSQL takes an advisory lock, so concurrent
runs are safe) and prints the schema version. On PostgreSQL it can then grant a runtime role the
data privileges the API needs and nothing more: CONNECT, schema USAGE, SELECT/INSERT/UPDATE/DELETE
on tables and USAGE/SELECT on sequences, now and for tables this role creates later. The runtime
role gets no CREATE, ALTER or ownership, so the API cannot change the schema; the database
triggers that block audit rewrites and signed-off edits apply to it as to everyone.

--create-entra-principal first creates the role as a Microsoft Entra principal on Azure Database
for PostgreSQL (pgaadauth_create_principal, run in the 'postgres' database by an Entra
administrator) if it does not exist. The name is the managed identity's name.

--bootstrap-admin-org/--bootstrap-admin-subject register and activate the first account in the
clinician account registry, the deployed equivalent of `python -m app.accounts register --activate`
for an environment with no operator shell inside its network. It acts only when that subject has
never been registered in that organisation: an existing account, whatever its status, is left
exactly as it is, so a suspended or deactivated account is never reactivated this way. Both
transitions are audited (actor operator:cli, reason deploy_bootstrap). Roles still come only from
the identity provider's token.

Exit status: 0 success, 1 failure, 2 configuration error. Messages never include credentials.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Any

from . import db

ROLE_ENV = "STN_DB_RUNTIME_ROLE"
ENTRA_ENV = "STN_DB_CREATE_ENTRA_PRINCIPAL"
BOOTSTRAP_ORG_ENV = "STN_BOOTSTRAP_ADMIN_ORG"
BOOTSTRAP_SUBJECT_ENV = "STN_BOOTSTRAP_ADMIN_SUBJECT"
BOOTSTRAP_REASON = "deploy_bootstrap"
_ORG_NAME = re.compile(r"^[A-Za-z0-9_.:-]{1,128}$")
_ROLE_NAME = re.compile(r"^[A-Za-z0-9_.@-]{1,63}$")


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _check_role_name(name: str) -> str:
    if not _ROLE_NAME.fullmatch(name):
        raise ValueError("Runtime role name must be 1-63 characters: letters, digits, _ . @ -")
    return name


def create_entra_principal(url: str, psycopg: Any, role: str) -> bool:
    """Create the Entra principal for a managed identity if it does not exist. True if created."""
    from psycopg import conninfo

    admin_url = conninfo.make_conninfo(url, dbname="postgres")
    with db.pg_connect(admin_url, psycopg, autocommit=True) as raw:
        exists = raw.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone()
        if exists:
            return False
        raw.execute("SELECT * FROM pgaadauth_create_principal(%s, false, false)", (role,))
        return True


def grant_runtime_role(url: str, psycopg: Any, role: str) -> None:
    from psycopg import sql

    ident = sql.Identifier(role)
    statements = [
        sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(_current_database(url, psycopg)), ident),
        sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(ident),
        sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {}").format(ident),
        sql.SQL("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {}").format(ident),
        sql.SQL(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}"
        ).format(ident),
        sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT ON SEQUENCES TO {}").format(ident),
    ]
    with db.pg_connect(url, psycopg, autocommit=True) as raw:
        if not raw.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)).fetchone():
            raise LookupError("The runtime role does not exist in this database server.")
        with raw.transaction():
            for statement in statements:
                raw.execute(statement)


def bootstrap_admin(org: str, subject: str) -> bool:
    """Register and activate a never-registered subject. True if registered now, False if it already was."""
    from . import accounts

    if not _ORG_NAME.fullmatch(org):
        raise ValueError("Bootstrap organisation must be 1-128 characters: letters, digits, _ . : -")
    subject = accounts.valid_subject(subject)
    with db.transaction() as conn:
        if accounts.account_row(conn, org, subject) is not None:
            return False
    try:
        accounts.invite(accounts.CLI_ACTOR, org, subject, BOOTSTRAP_REASON)
    except accounts.AccountTransitionNotAllowed:
        return False  # registered concurrently; leave it as it is
    accounts.change_status(accounts.CLI_ACTOR, org, subject, "activate", BOOTSTRAP_REASON)
    return True


def _current_database(url: str, psycopg: Any) -> str:
    with db.pg_connect(url, psycopg, autocommit=True) as raw:
        return raw.execute("SELECT current_database()").fetchone()[0]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.migrate", description=__doc__.split("\n\n")[0])
    parser.add_argument("--status", action="store_true", help="print the applied and expected versions only")
    parser.add_argument("--grant-runtime-role", default=os.getenv(ROLE_ENV, "").strip() or None)
    parser.add_argument("--create-entra-principal", action="store_true", default=_truthy(os.getenv(ENTRA_ENV)))
    parser.add_argument("--bootstrap-admin-org", default=os.getenv(BOOTSTRAP_ORG_ENV, "").strip() or None)
    parser.add_argument("--bootstrap-admin-subject", default=os.getenv(BOOTSTRAP_SUBJECT_ENV, "").strip() or None)
    args = parser.parse_args(argv)
    if bool(args.bootstrap_admin_org) != bool(args.bootstrap_admin_subject):
        print("configuration error: the bootstrap admin needs both an organisation and a subject", file=sys.stderr)
        return 2

    try:
        kind = db.dialect()
        expected = db.head_version(kind)
        if args.status:
            print(f"schema version {db.schema_version()}; this build expects {expected}")
            return 0
        version = db.migrate()
        print(f"migrations applied: schema version {version} (this build expects {expected})")
        if args.grant_runtime_role:
            if kind != "postgres":
                print("runtime role grants apply to PostgreSQL only", file=sys.stderr)
                return 2
            role = _check_role_name(args.grant_runtime_role)
            psycopg = db._pg_driver()
            url = os.environ[db.URL_ENV].strip()
            if args.create_entra_principal and create_entra_principal(url, psycopg, role):
                print("created the runtime role as a Microsoft Entra principal")
            grant_runtime_role(url, psycopg, role)
            print("granted data privileges to the runtime role")
        if version != expected:
            return 1
        if args.bootstrap_admin_org:
            created = bootstrap_admin(args.bootstrap_admin_org, args.bootstrap_admin_subject)
            print("bootstrap admin registered and activated" if created
                  else "bootstrap admin already registered; left unchanged")
        return 0
    except (db.StoreNotConfigured, ValueError, LookupError) as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 - report the class only; never echo connection details
        print(f"migration failed: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

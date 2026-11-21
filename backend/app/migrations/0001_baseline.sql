-- Baseline: tables that existed before the migration framework was introduced.
CREATE TABLE IF NOT EXISTS client_records (
    id         TEXT PRIMARY KEY,
    owner_sub  TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    ciphertext BLOB NOT NULL
);
CREATE TABLE IF NOT EXISTS audit_log (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ts        TEXT NOT NULL,
    actor_sub TEXT NOT NULL,
    action    TEXT NOT NULL,
    record_id TEXT,
    outcome   TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS role_assignments (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    subject    TEXT NOT NULL,
    role       TEXT NOT NULL,
    granted_by TEXT NOT NULL,
    granted_at TEXT NOT NULL,
    revoked_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_role_assignments_subject ON role_assignments (subject);
CREATE TABLE IF NOT EXISTS audit_chain (
    seq         INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL,
    actor       TEXT NOT NULL,
    action      TEXT NOT NULL,
    subject_ref TEXT NOT NULL,
    detail      TEXT NOT NULL,
    prev_hash   TEXT NOT NULL,
    hash        TEXT NOT NULL
);
CREATE TRIGGER IF NOT EXISTS audit_chain_no_update BEFORE UPDATE ON audit_chain
BEGIN SELECT RAISE(ABORT, 'audit trail is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_chain_no_delete BEFORE DELETE ON audit_chain
BEGIN SELECT RAISE(ABORT, 'audit trail is append-only'); END;
CREATE TABLE IF NOT EXISTS onboarding_cases (
    id         TEXT PRIMARY KEY,
    subject    TEXT NOT NULL,
    stage      TEXT NOT NULL,
    suspended  INTEGER NOT NULL DEFAULT 0,
    evidence   TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_onboarding_subject ON onboarding_cases (subject);

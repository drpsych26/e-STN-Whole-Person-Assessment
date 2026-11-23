-- STN API schema v1 (SQLite: tests and local synthetic runs only).
-- Clinical payloads are stored only as AES-256-GCM ciphertext. Audit rows hold no payloads.

CREATE TABLE IF NOT EXISTS client_records (
    id         TEXT PRIMARY KEY,
    owner_sub  TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    ciphertext BLOB NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ts          TEXT NOT NULL,
    actor_sub   TEXT NOT NULL,
    action      TEXT NOT NULL,
    object_type TEXT NOT NULL,
    record_id   TEXT,
    outcome     TEXT NOT NULL,
    prev_hash   TEXT NOT NULL,
    hash        TEXT NOT NULL UNIQUE
);
CREATE TRIGGER IF NOT EXISTS audit_events_no_update BEFORE UPDATE ON audit_events
BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_events_no_delete BEFORE DELETE ON audit_events
BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END;

CREATE TABLE IF NOT EXISTS assessments (
    id                TEXT PRIMARY KEY,
    client_id         TEXT NOT NULL REFERENCES client_records(id),
    author_sub        TEXT NOT NULL,
    version           INTEGER NOT NULL CHECK (version >= 1),
    parent_id         TEXT REFERENCES assessments(id),
    form_id           TEXT NOT NULL,
    form_version      TEXT NOT NULL,
    state             TEXT NOT NULL CHECK (state IN ('draft', 'submitted', 'in_review', 'returned', 'signed_off')),
    revision          INTEGER NOT NULL,
    submission        INTEGER NOT NULL DEFAULT 0,
    ciphertext        BLOB NOT NULL,
    note_ciphertext   BLOB,
    content_hash      TEXT,
    reviewer_sub      TEXT,
    created_at        TEXT NOT NULL,
    updated_at        TEXT NOT NULL,
    submitted_at      TEXT,
    review_started_at TEXT,
    returned_at       TEXT,
    signed_off_by     TEXT,
    signed_off_at     TEXT
);
CREATE INDEX IF NOT EXISTS assessments_client_idx ON assessments (client_id);
CREATE INDEX IF NOT EXISTS assessments_state_idx ON assessments (state);
CREATE TRIGGER IF NOT EXISTS assessments_signed_off_immutable BEFORE UPDATE ON assessments
WHEN OLD.state = 'signed_off'
BEGIN SELECT RAISE(ABORT, 'signed-off assessments are immutable'); END;
CREATE TRIGGER IF NOT EXISTS assessments_no_delete BEFORE DELETE ON assessments
BEGIN SELECT RAISE(ABORT, 'assessments cannot be deleted'); END;

CREATE TABLE IF NOT EXISTS safety_flags (
    id              TEXT PRIMARY KEY,
    assessment_id   TEXT NOT NULL REFERENCES assessments(id),
    submission      INTEGER NOT NULL,
    code            TEXT NOT NULL,
    raised_by       TEXT NOT NULL,
    raised_at       TEXT NOT NULL,
    acknowledged_by TEXT,
    acknowledged_at TEXT,
    UNIQUE (assessment_id, submission, code)
);
CREATE TRIGGER IF NOT EXISTS safety_flags_no_delete BEFORE DELETE ON safety_flags
BEGIN SELECT RAISE(ABORT, 'safety flags cannot be deleted'); END;

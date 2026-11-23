-- STN API schema v1 (PostgreSQL). Applied once and recorded in schema_migrations.
-- Clinical payloads are stored only as AES-256-GCM ciphertext. Audit rows hold no payloads.
-- Timestamps are ISO-8601 UTC text so the audit hash chain verifies byte-for-byte.

CREATE TABLE IF NOT EXISTS client_records (
    id         TEXT PRIMARY KEY,
    owner_sub  TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    ciphertext BYTEA NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_events (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ts          TEXT NOT NULL,
    actor_sub   TEXT NOT NULL,
    action      TEXT NOT NULL,
    object_type TEXT NOT NULL,
    record_id   TEXT,
    outcome     TEXT NOT NULL,
    prev_hash   TEXT NOT NULL,
    hash        TEXT NOT NULL UNIQUE
);

CREATE OR REPLACE FUNCTION stn_reject_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION '%', TG_ARGV[0];
END;
$$;

DROP TRIGGER IF EXISTS audit_events_append_only ON audit_events;
CREATE TRIGGER audit_events_append_only BEFORE UPDATE OR DELETE ON audit_events
    FOR EACH ROW EXECUTE FUNCTION stn_reject_change('audit_events is append-only');
DROP TRIGGER IF EXISTS audit_events_no_truncate ON audit_events;
CREATE TRIGGER audit_events_no_truncate BEFORE TRUNCATE ON audit_events
    FOR EACH STATEMENT EXECUTE FUNCTION stn_reject_change('audit_events is append-only');

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
    ciphertext        BYTEA NOT NULL,
    note_ciphertext   BYTEA,
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

DROP TRIGGER IF EXISTS assessments_signed_off_immutable ON assessments;
CREATE TRIGGER assessments_signed_off_immutable BEFORE UPDATE ON assessments
    FOR EACH ROW WHEN (OLD.state = 'signed_off')
    EXECUTE FUNCTION stn_reject_change('signed-off assessments are immutable');
DROP TRIGGER IF EXISTS assessments_no_delete ON assessments;
CREATE TRIGGER assessments_no_delete BEFORE DELETE ON assessments
    FOR EACH ROW EXECUTE FUNCTION stn_reject_change('assessments cannot be deleted');

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
DROP TRIGGER IF EXISTS safety_flags_no_delete ON safety_flags;
CREATE TRIGGER safety_flags_no_delete BEFORE DELETE ON safety_flags
    FOR EACH ROW EXECUTE FUNCTION stn_reject_change('safety flags cannot be deleted');

-- STN API schema v7 (sqlite). Audit-chain export register (D-18).
-- Record of verified audit-chain exports to write-once storage. One row per export; append-only.
CREATE TABLE IF NOT EXISTS audit_exports (
    id             TEXT PRIMARY KEY,
    from_event_id  BIGINT NOT NULL,
    to_event_id    BIGINT NOT NULL,
    event_count    INTEGER NOT NULL,
    first_prev_hash TEXT NOT NULL,
    last_hash      TEXT NOT NULL,
    sha256         TEXT NOT NULL,
    sink           TEXT NOT NULL,
    object_name    TEXT NOT NULL,
    exported_at    TEXT NOT NULL,
    CHECK (to_event_id >= from_event_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS audit_exports_range_idx ON audit_exports (from_event_id);
CREATE TRIGGER IF NOT EXISTS audit_exports_append_only_u BEFORE UPDATE ON audit_exports
BEGIN SELECT RAISE(ABORT, 'audit export records are append-only'); END;
CREATE TRIGGER IF NOT EXISTS audit_exports_append_only_d BEFORE DELETE ON audit_exports
BEGIN SELECT RAISE(ABORT, 'audit export records are append-only'); END;

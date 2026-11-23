-- STN API schema v2 (SQLite: tests and local synthetic runs only).
-- Organisation scoping, consent records, legal holds, two-person disposal with
-- tombstones, export log, and key-rotation support. Synthetic data only.
-- Rows that existed before v2 are placed in organisation 'unassigned' and are not
-- visible to any real organisation until an operator reassigns them.

ALTER TABLE client_records ADD COLUMN org_id TEXT NOT NULL DEFAULT 'unassigned';
ALTER TABLE client_records ADD COLUMN disposed_at TEXT;
ALTER TABLE assessments ADD COLUMN org_id TEXT NOT NULL DEFAULT 'unassigned';
ALTER TABLE assessments ADD COLUMN disposed_at TEXT;
ALTER TABLE audit_events ADD COLUMN org_id TEXT;
ALTER TABLE audit_events ADD COLUMN content_hash TEXT;

CREATE INDEX IF NOT EXISTS client_records_org_idx ON client_records (org_id);
CREATE INDEX IF NOT EXISTS assessments_org_state_idx ON assessments (org_id, state);
CREATE INDEX IF NOT EXISTS audit_events_org_idx ON audit_events (org_id, id);

-- Signed-off assessments: only re-encryption (ciphertext columns) and disposal
-- (ciphertext emptied, disposed_at set) may change them. Disposed rows are final.
DROP TRIGGER IF EXISTS assessments_signed_off_immutable;
CREATE TRIGGER assessments_signed_off_immutable BEFORE UPDATE ON assessments
WHEN OLD.state = 'signed_off' AND (
    NEW.id IS NOT OLD.id OR NEW.client_id IS NOT OLD.client_id OR NEW.author_sub IS NOT OLD.author_sub
    OR NEW.version IS NOT OLD.version OR NEW.parent_id IS NOT OLD.parent_id OR NEW.form_id IS NOT OLD.form_id
    OR NEW.form_version IS NOT OLD.form_version OR NEW.state IS NOT OLD.state OR NEW.revision IS NOT OLD.revision
    OR NEW.submission IS NOT OLD.submission OR NEW.content_hash IS NOT OLD.content_hash
    OR NEW.reviewer_sub IS NOT OLD.reviewer_sub OR NEW.created_at IS NOT OLD.created_at
    OR NEW.updated_at IS NOT OLD.updated_at OR NEW.submitted_at IS NOT OLD.submitted_at
    OR NEW.review_started_at IS NOT OLD.review_started_at OR NEW.returned_at IS NOT OLD.returned_at
    OR NEW.signed_off_by IS NOT OLD.signed_off_by OR NEW.signed_off_at IS NOT OLD.signed_off_at
    OR NEW.org_id IS NOT OLD.org_id
)
BEGIN SELECT RAISE(ABORT, 'signed-off assessments are immutable'); END;

CREATE TRIGGER IF NOT EXISTS assessments_disposed_final BEFORE UPDATE ON assessments
WHEN OLD.disposed_at IS NOT NULL
BEGIN SELECT RAISE(ABORT, 'disposed records are final'); END;
CREATE TRIGGER IF NOT EXISTS client_records_disposed_final BEFORE UPDATE ON client_records
WHEN OLD.disposed_at IS NOT NULL
BEGIN SELECT RAISE(ABORT, 'disposed records are final'); END;
CREATE TRIGGER IF NOT EXISTS client_records_no_delete BEFORE DELETE ON client_records
BEGIN SELECT RAISE(ABORT, 'client records cannot be deleted; use the disposal workflow'); END;

CREATE TABLE IF NOT EXISTS consents (
    id               TEXT PRIMARY KEY,
    org_id           TEXT NOT NULL,
    client_id        TEXT NOT NULL REFERENCES client_records(id),
    scope            TEXT NOT NULL,
    consent_text_ref TEXT NOT NULL,
    captured_by      TEXT NOT NULL,
    captured_at      TEXT NOT NULL,
    withdrawn_by     TEXT,
    withdrawn_at     TEXT
);
CREATE INDEX IF NOT EXISTS consents_client_idx ON consents (org_id, client_id);
CREATE TRIGGER IF NOT EXISTS consents_no_delete BEFORE DELETE ON consents
BEGIN SELECT RAISE(ABORT, 'consent records cannot be deleted'); END;
CREATE TRIGGER IF NOT EXISTS consents_withdraw_only BEFORE UPDATE ON consents
WHEN OLD.withdrawn_at IS NOT NULL
    OR NEW.id IS NOT OLD.id OR NEW.org_id IS NOT OLD.org_id OR NEW.client_id IS NOT OLD.client_id
    OR NEW.scope IS NOT OLD.scope OR NEW.consent_text_ref IS NOT OLD.consent_text_ref
    OR NEW.captured_by IS NOT OLD.captured_by OR NEW.captured_at IS NOT OLD.captured_at
BEGIN SELECT RAISE(ABORT, 'consent records change only by a single withdrawal'); END;

CREATE TABLE IF NOT EXISTS legal_holds (
    id          TEXT PRIMARY KEY,
    org_id      TEXT NOT NULL,
    client_id   TEXT NOT NULL REFERENCES client_records(id),
    reason_code TEXT NOT NULL,
    placed_by   TEXT NOT NULL,
    placed_at   TEXT NOT NULL,
    released_by TEXT,
    released_at TEXT
);
CREATE INDEX IF NOT EXISTS legal_holds_client_idx ON legal_holds (org_id, client_id);
CREATE TRIGGER IF NOT EXISTS legal_holds_no_delete BEFORE DELETE ON legal_holds
BEGIN SELECT RAISE(ABORT, 'legal holds cannot be deleted'); END;
CREATE TRIGGER IF NOT EXISTS legal_holds_release_only BEFORE UPDATE ON legal_holds
WHEN OLD.released_at IS NOT NULL
    OR NEW.id IS NOT OLD.id OR NEW.org_id IS NOT OLD.org_id OR NEW.client_id IS NOT OLD.client_id
    OR NEW.reason_code IS NOT OLD.reason_code OR NEW.placed_by IS NOT OLD.placed_by
    OR NEW.placed_at IS NOT OLD.placed_at
BEGIN SELECT RAISE(ABORT, 'legal holds change only by a single release'); END;

CREATE TABLE IF NOT EXISTS disposals (
    id                    TEXT PRIMARY KEY,
    org_id                TEXT NOT NULL,
    client_id             TEXT NOT NULL REFERENCES client_records(id),
    reason_code           TEXT NOT NULL,
    state                 TEXT NOT NULL CHECK (state IN ('requested', 'cancelled', 'executed')),
    retention_period_days INTEGER NOT NULL,
    retention_anchor      TEXT NOT NULL,
    requested_by          TEXT NOT NULL,
    requested_at          TEXT NOT NULL,
    decided_by            TEXT,
    decided_at            TEXT,
    assessments_disposed  INTEGER
);
CREATE INDEX IF NOT EXISTS disposals_org_idx ON disposals (org_id, state);
CREATE TRIGGER IF NOT EXISTS disposals_no_delete BEFORE DELETE ON disposals
BEGIN SELECT RAISE(ABORT, 'disposal records cannot be deleted'); END;
CREATE TRIGGER IF NOT EXISTS disposals_final BEFORE UPDATE ON disposals
WHEN OLD.state <> 'requested'
BEGIN SELECT RAISE(ABORT, 'decided disposal records are final'); END;

CREATE TABLE IF NOT EXISTS exports (
    id            TEXT PRIMARY KEY,
    org_id        TEXT NOT NULL,
    assessment_id TEXT NOT NULL REFERENCES assessments(id),
    exported_by   TEXT NOT NULL,
    exported_at   TEXT NOT NULL,
    reason_code   TEXT NOT NULL,
    export_hash   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS exports_assessment_idx ON exports (org_id, assessment_id);
CREATE TRIGGER IF NOT EXISTS exports_no_update BEFORE UPDATE ON exports
BEGIN SELECT RAISE(ABORT, 'export log is append-only'); END;
CREATE TRIGGER IF NOT EXISTS exports_no_delete BEFORE DELETE ON exports
BEGIN SELECT RAISE(ABORT, 'export log is append-only'); END;

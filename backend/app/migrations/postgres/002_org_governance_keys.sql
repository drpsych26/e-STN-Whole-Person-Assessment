-- STN API schema v2 (PostgreSQL). Applied once and recorded in schema_migrations.
-- Organisation scoping, consent records, legal holds, two-person disposal with
-- tombstones, export log, and key-rotation support. Synthetic data only.
-- Rows that existed before v2 are placed in organisation 'unassigned' and are not
-- visible to any real organisation until an operator reassigns them.

ALTER TABLE client_records ADD COLUMN IF NOT EXISTS org_id TEXT NOT NULL DEFAULT 'unassigned';
ALTER TABLE client_records ADD COLUMN IF NOT EXISTS disposed_at TEXT;
ALTER TABLE assessments ADD COLUMN IF NOT EXISTS org_id TEXT NOT NULL DEFAULT 'unassigned';
ALTER TABLE assessments ADD COLUMN IF NOT EXISTS disposed_at TEXT;
ALTER TABLE audit_events ADD COLUMN IF NOT EXISTS org_id TEXT;
ALTER TABLE audit_events ADD COLUMN IF NOT EXISTS content_hash TEXT;

CREATE INDEX IF NOT EXISTS client_records_org_idx ON client_records (org_id);
CREATE INDEX IF NOT EXISTS assessments_org_state_idx ON assessments (org_id, state);
CREATE INDEX IF NOT EXISTS audit_events_org_idx ON audit_events (org_id, id);

-- Signed-off assessments: only re-encryption (ciphertext columns) and disposal
-- (ciphertext emptied, disposed_at set) may change them. Disposed rows are final.
DROP TRIGGER IF EXISTS assessments_signed_off_immutable ON assessments;
CREATE TRIGGER assessments_signed_off_immutable BEFORE UPDATE ON assessments
    FOR EACH ROW WHEN (OLD.state = 'signed_off' AND (
        NEW.id IS DISTINCT FROM OLD.id OR NEW.client_id IS DISTINCT FROM OLD.client_id
        OR NEW.author_sub IS DISTINCT FROM OLD.author_sub OR NEW.version IS DISTINCT FROM OLD.version
        OR NEW.parent_id IS DISTINCT FROM OLD.parent_id OR NEW.form_id IS DISTINCT FROM OLD.form_id
        OR NEW.form_version IS DISTINCT FROM OLD.form_version OR NEW.state IS DISTINCT FROM OLD.state
        OR NEW.revision IS DISTINCT FROM OLD.revision OR NEW.submission IS DISTINCT FROM OLD.submission
        OR NEW.content_hash IS DISTINCT FROM OLD.content_hash OR NEW.reviewer_sub IS DISTINCT FROM OLD.reviewer_sub
        OR NEW.created_at IS DISTINCT FROM OLD.created_at OR NEW.updated_at IS DISTINCT FROM OLD.updated_at
        OR NEW.submitted_at IS DISTINCT FROM OLD.submitted_at
        OR NEW.review_started_at IS DISTINCT FROM OLD.review_started_at
        OR NEW.returned_at IS DISTINCT FROM OLD.returned_at OR NEW.signed_off_by IS DISTINCT FROM OLD.signed_off_by
        OR NEW.signed_off_at IS DISTINCT FROM OLD.signed_off_at OR NEW.org_id IS DISTINCT FROM OLD.org_id
    ))
    EXECUTE FUNCTION stn_reject_change('signed-off assessments are immutable');

DROP TRIGGER IF EXISTS assessments_disposed_final ON assessments;
CREATE TRIGGER assessments_disposed_final BEFORE UPDATE ON assessments
    FOR EACH ROW WHEN (OLD.disposed_at IS NOT NULL)
    EXECUTE FUNCTION stn_reject_change('disposed records are final');
DROP TRIGGER IF EXISTS client_records_disposed_final ON client_records;
CREATE TRIGGER client_records_disposed_final BEFORE UPDATE ON client_records
    FOR EACH ROW WHEN (OLD.disposed_at IS NOT NULL)
    EXECUTE FUNCTION stn_reject_change('disposed records are final');
DROP TRIGGER IF EXISTS client_records_no_delete ON client_records;
CREATE TRIGGER client_records_no_delete BEFORE DELETE ON client_records
    FOR EACH ROW EXECUTE FUNCTION stn_reject_change('client records cannot be deleted; use the disposal workflow');

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
DROP TRIGGER IF EXISTS consents_no_delete ON consents;
CREATE TRIGGER consents_no_delete BEFORE DELETE ON consents
    FOR EACH ROW EXECUTE FUNCTION stn_reject_change('consent records cannot be deleted');
DROP TRIGGER IF EXISTS consents_withdraw_only ON consents;
CREATE TRIGGER consents_withdraw_only BEFORE UPDATE ON consents
    FOR EACH ROW WHEN (
        OLD.withdrawn_at IS NOT NULL
        OR NEW.id IS DISTINCT FROM OLD.id OR NEW.org_id IS DISTINCT FROM OLD.org_id
        OR NEW.client_id IS DISTINCT FROM OLD.client_id OR NEW.scope IS DISTINCT FROM OLD.scope
        OR NEW.consent_text_ref IS DISTINCT FROM OLD.consent_text_ref
        OR NEW.captured_by IS DISTINCT FROM OLD.captured_by OR NEW.captured_at IS DISTINCT FROM OLD.captured_at
    )
    EXECUTE FUNCTION stn_reject_change('consent records change only by a single withdrawal');

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
DROP TRIGGER IF EXISTS legal_holds_no_delete ON legal_holds;
CREATE TRIGGER legal_holds_no_delete BEFORE DELETE ON legal_holds
    FOR EACH ROW EXECUTE FUNCTION stn_reject_change('legal holds cannot be deleted');
DROP TRIGGER IF EXISTS legal_holds_release_only ON legal_holds;
CREATE TRIGGER legal_holds_release_only BEFORE UPDATE ON legal_holds
    FOR EACH ROW WHEN (
        OLD.released_at IS NOT NULL
        OR NEW.id IS DISTINCT FROM OLD.id OR NEW.org_id IS DISTINCT FROM OLD.org_id
        OR NEW.client_id IS DISTINCT FROM OLD.client_id OR NEW.reason_code IS DISTINCT FROM OLD.reason_code
        OR NEW.placed_by IS DISTINCT FROM OLD.placed_by OR NEW.placed_at IS DISTINCT FROM OLD.placed_at
    )
    EXECUTE FUNCTION stn_reject_change('legal holds change only by a single release');

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
DROP TRIGGER IF EXISTS disposals_no_delete ON disposals;
CREATE TRIGGER disposals_no_delete BEFORE DELETE ON disposals
    FOR EACH ROW EXECUTE FUNCTION stn_reject_change('disposal records cannot be deleted');
DROP TRIGGER IF EXISTS disposals_final ON disposals;
CREATE TRIGGER disposals_final BEFORE UPDATE ON disposals
    FOR EACH ROW WHEN (OLD.state <> 'requested')
    EXECUTE FUNCTION stn_reject_change('decided disposal records are final');

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
DROP TRIGGER IF EXISTS exports_append_only ON exports;
CREATE TRIGGER exports_append_only BEFORE UPDATE OR DELETE ON exports
    FOR EACH ROW EXECUTE FUNCTION stn_reject_change('export log is append-only');

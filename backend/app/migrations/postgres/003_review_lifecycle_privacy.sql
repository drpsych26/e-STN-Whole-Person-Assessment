-- STN API schema v3 (PostgreSQL). Applied once and recorded in schema_migrations.
-- Reviewer assignment, clinician account registry with two-person reactivation,
-- and client access / correction requests (Privacy Act 2020 IPP 6 and IPP 7).
-- Synthetic data only.

-- Reviewer assignment: one row per assignment; a reassignment ends the previous row.
CREATE TABLE IF NOT EXISTS review_assignments (
    id            TEXT PRIMARY KEY,
    org_id        TEXT NOT NULL,
    assessment_id TEXT NOT NULL REFERENCES assessments(id),
    submission    INTEGER NOT NULL,
    reviewer_sub  TEXT NOT NULL,
    assigned_by   TEXT NOT NULL,
    assigned_at   TEXT NOT NULL,
    ended_by      TEXT,
    ended_at      TEXT,
    end_reason    TEXT
);
CREATE INDEX IF NOT EXISTS review_assignments_current_idx
    ON review_assignments (org_id, assessment_id, submission, ended_at);
DROP TRIGGER IF EXISTS review_assignments_no_delete ON review_assignments;
CREATE TRIGGER review_assignments_no_delete BEFORE DELETE ON review_assignments
    FOR EACH ROW EXECUTE FUNCTION stn_reject_change('review assignments cannot be deleted');
DROP TRIGGER IF EXISTS review_assignments_end_only ON review_assignments;
CREATE TRIGGER review_assignments_end_only BEFORE UPDATE ON review_assignments
    FOR EACH ROW WHEN (OLD.ended_at IS NOT NULL
        OR NEW.id IS DISTINCT FROM OLD.id OR NEW.org_id IS DISTINCT FROM OLD.org_id
        OR NEW.assessment_id IS DISTINCT FROM OLD.assessment_id OR NEW.submission IS DISTINCT FROM OLD.submission
        OR NEW.reviewer_sub IS DISTINCT FROM OLD.reviewer_sub OR NEW.assigned_by IS DISTINCT FROM OLD.assigned_by
        OR NEW.assigned_at IS DISTINCT FROM OLD.assigned_at)
    EXECUTE FUNCTION stn_reject_change('review assignments change only by a single end');

-- Clinician account registry: organisation-level status for token subjects.
CREATE TABLE IF NOT EXISTS clinician_accounts (
    org_id             TEXT NOT NULL,
    subject            TEXT NOT NULL,
    status             TEXT NOT NULL CHECK (status IN ('invited', 'active', 'suspended', 'deactivated')),
    invited_by         TEXT NOT NULL,
    invited_at         TEXT NOT NULL,
    status_reason_code TEXT,
    status_changed_by  TEXT NOT NULL,
    status_changed_at  TEXT NOT NULL,
    last_seen_at       TEXT,
    last_roles         TEXT,
    PRIMARY KEY (org_id, subject)
);
DROP TRIGGER IF EXISTS clinician_accounts_no_delete ON clinician_accounts;
CREATE TRIGGER clinician_accounts_no_delete BEFORE DELETE ON clinician_accounts
    FOR EACH ROW EXECUTE FUNCTION stn_reject_change('clinician accounts cannot be deleted; deactivate instead');

CREATE TABLE IF NOT EXISTS account_events (
    id          TEXT PRIMARY KEY,
    org_id      TEXT NOT NULL,
    subject     TEXT NOT NULL,
    from_status TEXT,
    to_status   TEXT NOT NULL,
    reason_code TEXT,
    actor       TEXT NOT NULL,
    at          TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS account_events_subject_idx ON account_events (org_id, subject, at);
DROP TRIGGER IF EXISTS account_events_append_only ON account_events;
CREATE TRIGGER account_events_append_only BEFORE UPDATE OR DELETE ON account_events
    FOR EACH ROW EXECUTE FUNCTION stn_reject_change('account events are append-only');

CREATE TABLE IF NOT EXISTS account_reactivations (
    id           TEXT PRIMARY KEY,
    org_id       TEXT NOT NULL,
    subject      TEXT NOT NULL,
    reason_code  TEXT NOT NULL,
    state        TEXT NOT NULL CHECK (state IN ('requested', 'approved', 'cancelled')),
    requested_by TEXT NOT NULL,
    requested_at TEXT NOT NULL,
    decided_by   TEXT,
    decided_at   TEXT
);
CREATE INDEX IF NOT EXISTS account_reactivations_idx ON account_reactivations (org_id, subject, state);
DROP TRIGGER IF EXISTS account_reactivations_no_delete ON account_reactivations;
CREATE TRIGGER account_reactivations_no_delete BEFORE DELETE ON account_reactivations
    FOR EACH ROW EXECUTE FUNCTION stn_reject_change('reactivation records cannot be deleted');
DROP TRIGGER IF EXISTS account_reactivations_final ON account_reactivations;
CREATE TRIGGER account_reactivations_final BEFORE UPDATE ON account_reactivations
    FOR EACH ROW WHEN (OLD.state <> 'requested')
    EXECUTE FUNCTION stn_reject_change('decided reactivation records are final');

-- Client access and correction requests (metadata only; no clinical payloads).
CREATE TABLE IF NOT EXISTS privacy_requests (
    id                    TEXT PRIMARY KEY,
    org_id                TEXT NOT NULL,
    client_id             TEXT NOT NULL REFERENCES client_records(id),
    kind                  TEXT NOT NULL CHECK (kind IN ('access', 'correction')),
    received_on           TEXT NOT NULL,
    working_days          INTEGER,
    due_on                TEXT,
    state                 TEXT NOT NULL CHECK (state IN ('open', 'responded', 'closed')),
    logged_by             TEXT NOT NULL,
    logged_at             TEXT NOT NULL,
    responded_by          TEXT,
    responded_at          TEXT,
    response_kind         TEXT,
    response_hash         TEXT,
    amended_assessment_id TEXT,
    outcome_code          TEXT,
    closed_by             TEXT,
    closed_at             TEXT
);
CREATE INDEX IF NOT EXISTS privacy_requests_org_idx ON privacy_requests (org_id, state, due_on);
DROP TRIGGER IF EXISTS privacy_requests_no_delete ON privacy_requests;
CREATE TRIGGER privacy_requests_no_delete BEFORE DELETE ON privacy_requests
    FOR EACH ROW EXECUTE FUNCTION stn_reject_change('privacy requests cannot be deleted');
DROP TRIGGER IF EXISTS privacy_requests_closed_final ON privacy_requests;
CREATE TRIGGER privacy_requests_closed_final BEFORE UPDATE ON privacy_requests
    FOR EACH ROW WHEN (OLD.state = 'closed')
    EXECUTE FUNCTION stn_reject_change('closed privacy requests are final');
DROP TRIGGER IF EXISTS privacy_requests_fixed_fields ON privacy_requests;
CREATE TRIGGER privacy_requests_fixed_fields BEFORE UPDATE ON privacy_requests
    FOR EACH ROW WHEN (NEW.id IS DISTINCT FROM OLD.id OR NEW.org_id IS DISTINCT FROM OLD.org_id
        OR NEW.client_id IS DISTINCT FROM OLD.client_id OR NEW.kind IS DISTINCT FROM OLD.kind
        OR NEW.received_on IS DISTINCT FROM OLD.received_on OR NEW.working_days IS DISTINCT FROM OLD.working_days
        OR NEW.due_on IS DISTINCT FROM OLD.due_on OR NEW.logged_by IS DISTINCT FROM OLD.logged_by
        OR NEW.logged_at IS DISTINCT FROM OLD.logged_at)
    EXECUTE FUNCTION stn_reject_change('privacy request intake fields cannot change');

-- Statements of correction (IPP 7): encrypted, attached to the client's records.
CREATE TABLE IF NOT EXISTS correction_statements (
    id                   TEXT PRIMARY KEY,
    org_id               TEXT NOT NULL,
    client_id            TEXT NOT NULL REFERENCES client_records(id),
    privacy_request_id   TEXT NOT NULL REFERENCES privacy_requests(id),
    statement_ciphertext BYTEA NOT NULL,
    attached_by          TEXT NOT NULL,
    attached_at          TEXT NOT NULL,
    disposed_at          TEXT
);
CREATE INDEX IF NOT EXISTS correction_statements_client_idx ON correction_statements (org_id, client_id);
DROP TRIGGER IF EXISTS correction_statements_no_delete ON correction_statements;
CREATE TRIGGER correction_statements_no_delete BEFORE DELETE ON correction_statements
    FOR EACH ROW EXECUTE FUNCTION stn_reject_change('correction statements cannot be deleted; use the disposal workflow');
-- Only re-encryption (ciphertext) and disposal (ciphertext emptied, disposed_at set) may change a row.
DROP TRIGGER IF EXISTS correction_statements_fixed_fields ON correction_statements;
CREATE TRIGGER correction_statements_fixed_fields BEFORE UPDATE ON correction_statements
    FOR EACH ROW WHEN (OLD.disposed_at IS NOT NULL
        OR NEW.id IS DISTINCT FROM OLD.id OR NEW.org_id IS DISTINCT FROM OLD.org_id
        OR NEW.client_id IS DISTINCT FROM OLD.client_id OR NEW.privacy_request_id IS DISTINCT FROM OLD.privacy_request_id
        OR NEW.attached_by IS DISTINCT FROM OLD.attached_by OR NEW.attached_at IS DISTINCT FROM OLD.attached_at)
    EXECUTE FUNCTION stn_reject_change('correction statements change only by re-encryption or disposal');

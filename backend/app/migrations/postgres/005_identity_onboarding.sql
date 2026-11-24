-- STN API schema v5 (PostgreSQL).
-- Identity verification events, client accounts and acknowledgements, clinician registrations, attestations.
-- Identity-provider verification events. Authenticated by the provider's signature;
-- (issuer, event_id) is unique, so a replayed event is refused. Identifiers and codes only.
CREATE TABLE IF NOT EXISTS identity_verification_events (
    issuer      TEXT NOT NULL,
    event_id    TEXT NOT NULL,
    subject     TEXT NOT NULL,
    kind        TEXT NOT NULL CHECK (kind IN ('email', 'phone', 'mfa')),
    issued_at   TEXT NOT NULL,
    received_at TEXT NOT NULL,
    PRIMARY KEY (issuer, event_id)
);
CREATE INDEX IF NOT EXISTS identity_verification_subject_idx ON identity_verification_events (subject, kind);

-- Client accounts: one token subject per client record per organisation.
-- invited (code issued, no subject yet) -> provisional (claimed) -> active -> suspended / deactivated.
CREATE TABLE IF NOT EXISTS client_accounts (
    org_id             TEXT NOT NULL,
    client_id          TEXT NOT NULL REFERENCES client_records(id),
    subject            TEXT,
    status             TEXT NOT NULL CHECK (status IN ('invited', 'provisional', 'active', 'suspended', 'deactivated')),
    invite_code_sha256 TEXT,
    invite_expires_at  TEXT,
    invited_by         TEXT NOT NULL,
    invited_at         TEXT NOT NULL,
    claimed_at         TEXT,
    activated_by       TEXT,
    activated_at       TEXT,
    status_reason_code TEXT,
    status_changed_by  TEXT NOT NULL,
    status_changed_at  TEXT NOT NULL,
    PRIMARY KEY (org_id, client_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS client_accounts_subject_idx ON client_accounts (org_id, subject);
CREATE UNIQUE INDEX IF NOT EXISTS client_accounts_invite_idx ON client_accounts (invite_code_sha256);

-- Versioned acknowledgements by a client (terms, privacy notice, consent). Append-only.
CREATE TABLE IF NOT EXISTS client_acknowledgements (
    id          TEXT PRIMARY KEY,
    org_id      TEXT NOT NULL,
    subject     TEXT NOT NULL,
    kind        TEXT NOT NULL CHECK (kind IN ('terms', 'privacy_notice', 'consent')),
    version     TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS client_acknowledgements_idx ON client_acknowledgements (org_id, subject, kind, version);

-- Clinician professional registration details, as submitted by the clinician. Unverified until attested.
CREATE TABLE IF NOT EXISTS clinician_registrations (
    id                  TEXT PRIMARY KEY,
    org_id              TEXT NOT NULL,
    subject             TEXT NOT NULL,
    authority           TEXT NOT NULL,
    registration_number TEXT NOT NULL,
    scope_code          TEXT NOT NULL,
    expires_on          TEXT NOT NULL,
    submitted_at        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS clinician_registrations_subject_idx ON clinician_registrations (org_id, subject, submitted_at);

-- Attestations: a second person records that they checked a specific platform record against an
-- external source. reference_id must be a record of the matching type in the same organisation.
CREATE TABLE IF NOT EXISTS attestations (
    id              TEXT PRIMARY KEY,
    org_id          TEXT NOT NULL,
    kind            TEXT NOT NULL CHECK (kind IN ('registration_verified')),
    reference_type  TEXT NOT NULL CHECK (reference_type IN ('clinician_registration')),
    reference_id    TEXT NOT NULL,
    subject         TEXT NOT NULL,
    source_url      TEXT NOT NULL,
    checked_on      TEXT NOT NULL,
    attested_by     TEXT NOT NULL,
    attested_at     TEXT NOT NULL,
    revoked_by      TEXT,
    revoked_at      TEXT,
    CHECK (attested_by <> subject)
);
CREATE INDEX IF NOT EXISTS attestations_reference_idx ON attestations (org_id, reference_type, reference_id);
DROP TRIGGER IF EXISTS identity_verification_append_only ON identity_verification_events;
CREATE TRIGGER identity_verification_append_only BEFORE UPDATE OR DELETE ON identity_verification_events
    FOR EACH ROW EXECUTE FUNCTION stn_reject_change('verification events are append-only');
DROP TRIGGER IF EXISTS client_accounts_no_delete ON client_accounts;
CREATE TRIGGER client_accounts_no_delete BEFORE DELETE ON client_accounts
    FOR EACH ROW EXECUTE FUNCTION stn_reject_change('client accounts cannot be deleted; deactivate instead');
DROP TRIGGER IF EXISTS client_accounts_final ON client_accounts;
CREATE TRIGGER client_accounts_final BEFORE UPDATE ON client_accounts
    FOR EACH ROW WHEN (OLD.status = 'deactivated' OR NEW.org_id IS DISTINCT FROM OLD.org_id
        OR NEW.client_id IS DISTINCT FROM OLD.client_id
        OR (OLD.subject IS NOT NULL AND NEW.subject IS DISTINCT FROM OLD.subject))
    EXECUTE FUNCTION stn_reject_change('deactivated client accounts are final and a claimed subject cannot change');
DROP TRIGGER IF EXISTS client_acknowledgements_append_only ON client_acknowledgements;
CREATE TRIGGER client_acknowledgements_append_only BEFORE UPDATE OR DELETE ON client_acknowledgements
    FOR EACH ROW EXECUTE FUNCTION stn_reject_change('acknowledgements are append-only');
DROP TRIGGER IF EXISTS clinician_registrations_append_only ON clinician_registrations;
CREATE TRIGGER clinician_registrations_append_only BEFORE UPDATE OR DELETE ON clinician_registrations
    FOR EACH ROW EXECUTE FUNCTION stn_reject_change('registration records are append-only; submit a new one');
DROP TRIGGER IF EXISTS attestations_no_delete ON attestations;
CREATE TRIGGER attestations_no_delete BEFORE DELETE ON attestations
    FOR EACH ROW EXECUTE FUNCTION stn_reject_change('attestations cannot be deleted; revoke instead');
DROP TRIGGER IF EXISTS attestations_revoke_only ON attestations;
CREATE TRIGGER attestations_revoke_only BEFORE UPDATE ON attestations
    FOR EACH ROW WHEN (OLD.revoked_at IS NOT NULL OR NEW.id IS DISTINCT FROM OLD.id
        OR NEW.org_id IS DISTINCT FROM OLD.org_id OR NEW.kind IS DISTINCT FROM OLD.kind
        OR NEW.reference_type IS DISTINCT FROM OLD.reference_type OR NEW.reference_id IS DISTINCT FROM OLD.reference_id
        OR NEW.subject IS DISTINCT FROM OLD.subject OR NEW.source_url IS DISTINCT FROM OLD.source_url
        OR NEW.checked_on IS DISTINCT FROM OLD.checked_on OR NEW.attested_by IS DISTINCT FROM OLD.attested_by
        OR NEW.attested_at IS DISTINCT FROM OLD.attested_at)
    EXECUTE FUNCTION stn_reject_change('attestations change only by a single revocation');

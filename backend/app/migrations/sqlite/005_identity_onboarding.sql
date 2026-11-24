-- STN API schema v5 (SQLite: tests and local synthetic runs only).
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
CREATE TRIGGER IF NOT EXISTS identity_verification_no_change BEFORE UPDATE ON identity_verification_events
BEGIN SELECT RAISE(ABORT, 'verification events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS identity_verification_no_delete BEFORE DELETE ON identity_verification_events
BEGIN SELECT RAISE(ABORT, 'verification events are append-only'); END;
CREATE TRIGGER IF NOT EXISTS client_accounts_no_delete BEFORE DELETE ON client_accounts
BEGIN SELECT RAISE(ABORT, 'client accounts cannot be deleted; deactivate instead'); END;
CREATE TRIGGER IF NOT EXISTS client_accounts_final BEFORE UPDATE ON client_accounts
WHEN OLD.status = 'deactivated' OR NEW.org_id IS NOT OLD.org_id OR NEW.client_id IS NOT OLD.client_id
    OR (OLD.subject IS NOT NULL AND NEW.subject IS NOT OLD.subject)
BEGIN SELECT RAISE(ABORT, 'deactivated client accounts are final and a claimed subject cannot change'); END;
CREATE TRIGGER IF NOT EXISTS client_acknowledgements_no_change BEFORE UPDATE ON client_acknowledgements
BEGIN SELECT RAISE(ABORT, 'acknowledgements are append-only'); END;
CREATE TRIGGER IF NOT EXISTS client_acknowledgements_no_delete BEFORE DELETE ON client_acknowledgements
BEGIN SELECT RAISE(ABORT, 'acknowledgements are append-only'); END;
CREATE TRIGGER IF NOT EXISTS clinician_registrations_no_change BEFORE UPDATE ON clinician_registrations
BEGIN SELECT RAISE(ABORT, 'registration records are append-only; submit a new one'); END;
CREATE TRIGGER IF NOT EXISTS clinician_registrations_no_delete BEFORE DELETE ON clinician_registrations
BEGIN SELECT RAISE(ABORT, 'registration records are append-only'); END;
CREATE TRIGGER IF NOT EXISTS attestations_no_delete BEFORE DELETE ON attestations
BEGIN SELECT RAISE(ABORT, 'attestations cannot be deleted; revoke instead'); END;
CREATE TRIGGER IF NOT EXISTS attestations_revoke_only BEFORE UPDATE ON attestations
WHEN OLD.revoked_at IS NOT NULL OR NEW.id IS NOT OLD.id OR NEW.org_id IS NOT OLD.org_id OR NEW.kind IS NOT OLD.kind
    OR NEW.reference_type IS NOT OLD.reference_type OR NEW.reference_id IS NOT OLD.reference_id
    OR NEW.subject IS NOT OLD.subject OR NEW.source_url IS NOT OLD.source_url OR NEW.checked_on IS NOT OLD.checked_on
    OR NEW.attested_by IS NOT OLD.attested_by OR NEW.attested_at IS NOT OLD.attested_at
BEGIN SELECT RAISE(ABORT, 'attestations change only by a single revocation'); END;

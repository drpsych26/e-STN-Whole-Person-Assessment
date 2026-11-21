-- Identity-provider verification events. Written only by the signed-event ingestion path.
CREATE TABLE IF NOT EXISTS verification_events (
    event_id    TEXT PRIMARY KEY,
    subject     TEXT NOT NULL,
    kind        TEXT NOT NULL,
    issuer      TEXT NOT NULL,
    issued_at   TEXT NOT NULL,
    received_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_verification_subject ON verification_events (subject, kind);

-- Customer acknowledgements of versioned texts (terms, privacy notice, consent).
CREATE TABLE IF NOT EXISTS acknowledgements (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    subject     TEXT NOT NULL,
    kind        TEXT NOT NULL,
    version     TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_ack_subject ON acknowledgements (subject, kind, version);

-- Staff attestations for onboarding stages. The attester must differ from the advancing actor.
CREATE TABLE IF NOT EXISTS attestations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id     TEXT NOT NULL,
    kind        TEXT NOT NULL,
    reference   TEXT NOT NULL,
    attested_by TEXT NOT NULL,
    recorded_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_attestation_case ON attestations (case_id, kind);

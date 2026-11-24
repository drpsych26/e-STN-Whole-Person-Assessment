-- STN API schema v6 (postgres). Notification outbox and preferences. Synthetic data only.
-- Notification outbox. Rows are written in the same transaction as the event that causes them,
-- so an event and its notification commit or roll back together. Recipients are token subjects;
-- no email address or phone number is stored. params_json holds identifiers and codes only.
CREATE TABLE IF NOT EXISTS notification_outbox (
    id                  TEXT PRIMARY KEY,
    org_id              TEXT NOT NULL,
    category            TEXT NOT NULL,
    template_id         TEXT NOT NULL,
    template_version    TEXT NOT NULL,
    recipient_sub       TEXT NOT NULL,
    params_json         TEXT NOT NULL,
    dedupe_key          TEXT NOT NULL,
    status              TEXT NOT NULL CHECK (status IN ('pending', 'sent', 'dead', 'suppressed')),
    attempts            INTEGER NOT NULL DEFAULT 0,
    next_attempt_at     TEXT NOT NULL,
    last_error_code     TEXT,
    provider_message_id TEXT,
    created_at          TEXT NOT NULL,
    sent_at             TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS notification_outbox_dedupe_idx ON notification_outbox (org_id, dedupe_key, recipient_sub);
CREATE INDEX IF NOT EXISTS notification_outbox_due_idx ON notification_outbox (status, next_attempt_at);

-- Opt-outs per subject and category. Safety and security categories cannot be opted out of.
CREATE TABLE IF NOT EXISTS notification_preferences (
    org_id     TEXT NOT NULL,
    subject    TEXT NOT NULL,
    category   TEXT NOT NULL,
    opted_out  INTEGER NOT NULL CHECK (opted_out IN (0, 1)),
    updated_at TEXT NOT NULL,
    PRIMARY KEY (org_id, subject, category)
);
DROP TRIGGER IF EXISTS notification_outbox_no_delete ON notification_outbox;
CREATE TRIGGER notification_outbox_no_delete BEFORE DELETE ON notification_outbox
    FOR EACH ROW EXECUTE FUNCTION stn_reject_change('notification records cannot be deleted');
DROP TRIGGER IF EXISTS notification_outbox_fixed ON notification_outbox;
CREATE TRIGGER notification_outbox_fixed BEFORE UPDATE ON notification_outbox
    FOR EACH ROW WHEN (OLD.status IN ('sent', 'dead', 'suppressed') OR NEW.id IS DISTINCT FROM OLD.id
        OR NEW.org_id IS DISTINCT FROM OLD.org_id OR NEW.recipient_sub IS DISTINCT FROM OLD.recipient_sub
        OR NEW.params_json IS DISTINCT FROM OLD.params_json OR NEW.template_id IS DISTINCT FROM OLD.template_id
        OR NEW.dedupe_key IS DISTINCT FROM OLD.dedupe_key)
    EXECUTE FUNCTION stn_reject_change('finished notifications are final and content cannot change');

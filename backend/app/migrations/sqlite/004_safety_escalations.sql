-- STN API schema v4 (SQLite: tests and local synthetic runs only).
-- Safety escalations: open -> acknowledged -> resolved, with ownership, timestamps and a
-- documented, coded resolution. Codes and identifiers only; no free text, no clinical content.
-- Severity tiers follow the four-level matrix in docs/clinical/SAFETY-ESCALATION-MATRIX.md,
-- which is PENDING CLINICAL APPROVAL. Synthetic data only.
CREATE TABLE IF NOT EXISTS safety_escalations (
    id                 TEXT PRIMARY KEY,
    org_id             TEXT NOT NULL,
    client_id          TEXT NOT NULL REFERENCES client_records(id),
    assessment_id      TEXT REFERENCES assessments(id),
    source             TEXT NOT NULL CHECK (source IN ('assessment_item', 'safety_flag', 'clinician_report', 'client_contact', 'third_party_report')),
    severity           TEXT NOT NULL CHECK (severity IN ('routine_monitoring', 'increased_concern', 'urgent_assessment', 'immediate_emergency')),
    status             TEXT NOT NULL CHECK (status IN ('open', 'acknowledged', 'resolved')),
    opened_by          TEXT NOT NULL,
    opened_at          TEXT NOT NULL,
    owner_sub          TEXT,
    acknowledged_at    TEXT,
    resolved_by        TEXT,
    resolved_at        TEXT,
    resolution_code    TEXT CHECK (resolution_code IN (
                           'emergency_services_contacted', 'referred_crisis_team', 'safety_plan_agreed',
                           'urgent_appointment_booked', 'monitoring_plan_documented', 'no_current_risk_documented')),
    documentation_ref  TEXT REFERENCES assessments(id)
);
CREATE INDEX IF NOT EXISTS safety_escalations_queue_idx ON safety_escalations (org_id, status, opened_at);
CREATE INDEX IF NOT EXISTS safety_escalations_client_idx ON safety_escalations (org_id, client_id, opened_at);
CREATE TRIGGER IF NOT EXISTS safety_escalations_no_delete BEFORE DELETE ON safety_escalations
BEGIN SELECT RAISE(ABORT, 'safety escalations cannot be deleted'); END;
CREATE TRIGGER IF NOT EXISTS safety_escalations_opening_fixed BEFORE UPDATE ON safety_escalations
WHEN OLD.status = 'resolved'
    OR NEW.id IS NOT OLD.id OR NEW.org_id IS NOT OLD.org_id OR NEW.client_id IS NOT OLD.client_id
    OR NEW.assessment_id IS NOT OLD.assessment_id OR NEW.source IS NOT OLD.source
    OR NEW.severity IS NOT OLD.severity OR NEW.opened_by IS NOT OLD.opened_by OR NEW.opened_at IS NOT OLD.opened_at
BEGIN SELECT RAISE(ABORT, 'safety escalation opening facts are fixed and resolved escalations are final'); END;

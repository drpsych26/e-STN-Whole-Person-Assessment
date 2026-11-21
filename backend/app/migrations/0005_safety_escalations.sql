-- Safety escalations. Append-only: rows cannot be deleted, and the opening facts
-- (subject, source, severity, opened_at, opened_by) cannot be changed.
-- Lifecycle: open -> acknowledged -> resolved. Each transition records who and when.
CREATE TABLE IF NOT EXISTS safety_escalations (
    id                   TEXT PRIMARY KEY,
    subject              TEXT NOT NULL,
    source               TEXT NOT NULL CHECK (source IN ('crisis_panel', 'assessment_item', 'clinician_report', 'manual')),
    severity             TEXT NOT NULL CHECK (severity IN ('urgent', 'high', 'routine')),
    status               TEXT NOT NULL CHECK (status IN ('open', 'acknowledged', 'resolved')),
    opened_at            TEXT NOT NULL,
    opened_by            TEXT NOT NULL,
    acknowledged_at      TEXT,
    acknowledged_by      TEXT,
    resolved_at          TEXT,
    resolved_by          TEXT,
    resolution_code      TEXT CHECK (resolution_code IN (
                         'safety_plan_agreed', 'referred_emergency', 'referred_crisis_team',
                         'no_risk_identified_documented', 'other_documented')),
    documentation_record TEXT
);
CREATE INDEX IF NOT EXISTS ix_safety_status ON safety_escalations (status, opened_at);
CREATE INDEX IF NOT EXISTS ix_safety_subject ON safety_escalations (subject, opened_at);
CREATE TRIGGER IF NOT EXISTS safety_no_delete BEFORE DELETE ON safety_escalations
BEGIN SELECT RAISE(ABORT, 'safety escalations are append-only'); END;
CREATE TRIGGER IF NOT EXISTS safety_opening_fixed BEFORE UPDATE ON safety_escalations
WHEN NEW.id IS NOT OLD.id OR NEW.subject IS NOT OLD.subject OR NEW.source IS NOT OLD.source
  OR NEW.severity IS NOT OLD.severity OR NEW.opened_at IS NOT OLD.opened_at OR NEW.opened_by IS NOT OLD.opened_by
BEGIN SELECT RAISE(ABORT, 'safety escalation opening facts are fixed'); END;

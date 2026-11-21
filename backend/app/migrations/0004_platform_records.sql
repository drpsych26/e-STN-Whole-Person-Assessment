-- Platform records that onboarding attestations must reference.
-- A record is created by a named staff member who holds the authorised role for its type.
-- Attestations may only cite an active record whose responsible staff member is the attester.
-- Records are append-only: no deletion, and only status may change (active -> withdrawn).
CREATE TABLE IF NOT EXISTS platform_records (
    id              TEXT PRIMARY KEY,
    record_type     TEXT NOT NULL CHECK (record_type IN
                    ('eligibility_review', 'screening_review', 'allocation', 'team_assignment')),
    case_id         TEXT NOT NULL REFERENCES onboarding_cases (id),
    subject         TEXT NOT NULL,
    responsible_sub TEXT NOT NULL,
    assignee_sub    TEXT,
    authorised_role TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'withdrawn')),
    created_by      TEXT NOT NULL,
    created_at      TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_platform_records_case ON platform_records (case_id, record_type);
CREATE TRIGGER IF NOT EXISTS platform_records_no_delete BEFORE DELETE ON platform_records
BEGIN SELECT RAISE(ABORT, 'platform records are append-only'); END;
CREATE TRIGGER IF NOT EXISTS platform_records_fields_fixed BEFORE UPDATE ON platform_records
WHEN NEW.id IS NOT OLD.id OR NEW.record_type IS NOT OLD.record_type OR NEW.case_id IS NOT OLD.case_id
  OR NEW.subject IS NOT OLD.subject OR NEW.responsible_sub IS NOT OLD.responsible_sub
  OR NEW.assignee_sub IS NOT OLD.assignee_sub OR NEW.authorised_role IS NOT OLD.authorised_role
  OR NEW.created_by IS NOT OLD.created_by OR NEW.created_at IS NOT OLD.created_at
  OR OLD.status = 'withdrawn' OR NEW.status NOT IN ('withdrawn')
BEGIN SELECT RAISE(ABORT, 'platform record fields are fixed; only active to withdrawn is permitted'); END;

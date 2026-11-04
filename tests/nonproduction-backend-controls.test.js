'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const contractPath = path.join('nonproduction-backend', 'control-contract.json');
const contract = JSON.parse(fs.readFileSync(contractPath, 'utf8'));

assert.equal(contract.boundary.classification, 'private non-production engineering design/test environment');
for (const field of ['production_deployment', 'clinical_operation', 'public_release', 'real_client_data']) {
  assert.equal(contract.boundary[field], 'prohibited', 'Boundary field must remain prohibited: ' + field);
}
assert.match(contract.boundary.permitted_data, /^synthetic/i);

assert.equal(contract.authentication.required, true);
assert.equal(contract.authentication.shared_credentials_prohibited, true);
assert.ok(contract.authentication.test_principal_prefixes.includes('TESTER-'));
assert.match(contract.authentication.model, /no live identity provider/i);

assert.equal(contract.authorization.required, true);
assert.equal(contract.authorization.enforcement, 'server-side deny-by-default policy contract');
assert.equal(contract.authorization.tenant_isolation_required, true);
assert.ok(contract.authorization.prohibited_actions.includes('access_real_client_data'));
assert.ok(contract.authorization.prohibited_actions.includes('bypass_audit'));

assert.equal(contract.audit.required, true);
assert.match(contract.audit.persistence_design, /append-only/i);
assert.match(contract.audit.payload_policy, /no assessment wording/i);
for (const field of ['event_id', 'occurred_at_utc', 'actor_id', 'tenant_id', 'action', 'decision', 'previous_event_hash']) {
  assert.ok(contract.audit.required_event_fields.includes(field), 'Missing audit field: ' + field);
}

assert.match(contract.encryption.required_in_transit, /TLS 1\.2 or later/);
assert.match(contract.encryption.required_at_rest, /encrypted/i);
assert.match(contract.encryption.key_management, /outside source control/i);
assert.doesNotMatch(JSON.stringify(contract), /password\s*[:=]|private[_ -]?key\s*[:=]|BEGIN [A-Z ]*PRIVATE KEY/i);

assert.equal(contract.privacy.analytics, 'disabled');
assert.match(contract.privacy.logging, /do not log source responses/i);
assert.match(contract.privacy.minimization, /synthetic/i);

for (const control of ['autonomous_diagnosis', 'autonomous_risk_disposition', 'autonomous_routing', 'autonomous_notification']) {
  assert.equal(contract.safety[control], false, 'Safety automation must be disabled: ' + control);
}
assert.match(contract.safety.safety_tag_handling, /non-clinical human-review-required state/i);
assert.match(contract.safety.production_safety_workflow, /^not implemented/i);

assert.equal(contract.source_traceability.allowed_client_scope, 'existing 25-item Flutter Part A mapping only');
assert.equal(contract.source_traceability.remaining_items, 'not implemented by this contract');
assert.ok(contract.promotion_gates.length >= 6);

console.log('PASS: non-production backend control contract enforces synthetic-only, security, privacy, audit, authorization, and safety design boundaries.');

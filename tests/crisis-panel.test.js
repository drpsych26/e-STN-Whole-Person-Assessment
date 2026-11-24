#!/usr/bin/env node
'use strict';
// Crisis panel model: synthetic scenarios, and drift check against the backend register.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const dir = path.join(root, 'frontend/crisis-panel');
const backend = JSON.parse(fs.readFileSync(path.join(root, 'backend/app/data/crisis_resources.json'), 'utf8'));
const sandbox = { window: {} };
vm.runInNewContext(fs.readFileSync(path.join(dir, 'crisis-resources.js'), 'utf8'), sandbox);
assert.deepEqual(JSON.parse(JSON.stringify(sandbox.window.STN_CRISIS_RESOURCES)), backend,
  'Bundled crisis-resources.js must equal backend/app/data/crisis_resources.json');
const { buildModel } = require(path.join(dir, 'crisis-panel-model.js'));

// 1. No region chosen: four tiers in order, 111 first, a prompt to choose a region.
let m = buildModel(backend, null);
assert.deepEqual(m.tiers.map(t => t.id), ['immediate_danger', 'urgent_crisis', 'distress', 'routine_support']);
assert.equal(m.tiers[0].items[0].tel, '111');
assert.equal(m.tiers[1].items[0].kind, 'choose_region');
assert.equal(m.provisional, true, 'Unapproved content must render as provisional');
assert.match(m.statement, /not an emergency service/);
assert.match(m.statement, /does not contact emergency services/);

// 2. Region with transcribed numbers: listed with a check-before-relying note.
m = buildModel(backend, 'canterbury');
const urgent = m.tiers[1].items;
assert.equal(urgent[0].tel, '0800920092');
assert.match(urgent[0].detail, /check before relying/);

// 3. Region we could not confirm: no number invented, directed to the source and 111.
m = buildModel(backend, 'auckland');
assert.equal(m.tiers[1].items[0].kind, 'see_source');
assert.equal(m.tiers[1].items[0].tel, undefined);
assert.match(m.tiers[1].items[0].detail, /call 111/);

// 4. Hours are always shown; Lifeline and the Suicide Crisis Helpline are never 24/7.
for (const tier of buildModel(backend, 'wellington').tiers) {
  for (const item of tier.items) {
    assert.ok(item.hours, `${item.label} must show hours`);
    if (['0800543354', '0508828865'].includes(item.tel)) assert.doesNotMatch(item.hours, /24/);
  }
}

// 5. Unknown region falls back to the prompt; a corrupt register is refused.
assert.equal(buildModel(backend, 'atlantis').tiers[1].items[0].kind, 'choose_region');
assert.throws(() => buildModel({ schema: 'other' }, null));

// 6. Component source: no innerHTML and no inline handlers (CSP script-src 'self').
const component = fs.readFileSync(path.join(dir, 'stn-crisis-panel.js'), 'utf8');
assert.doesNotMatch(component, /innerHTML|outerHTML|insertAdjacentHTML|eval\(|new Function/);
const demo = fs.readFileSync(path.join(dir, 'index.html'), 'utf8');
assert.doesNotMatch(demo, /\son[a-z]+=/i, 'No inline event handlers');
assert.doesNotMatch(demo, /<script>(?!\s*<\/script>)/, 'No inline scripts');
assert.match(demo, /script-src 'self'/);
assert.doesNotMatch(demo, /unsafe-inline/);

console.log('crisis panel: 6 scenario groups passed');

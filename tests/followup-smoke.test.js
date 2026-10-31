#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'prototype/follow-up-assessment.html'), 'utf8');
const scripts = [...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script\s*>/gi)]
  .map(match => match[1].trim())
  .filter(Boolean);
assert.equal(scripts.length, 1, 'Follow-up prototype must have one inline application script');
const style = (html.match(/<style>([\\s\\S]*?)<\\/style>/i) || [])[1] || '';
assert.match(style, /section,\\.card\\{[^}]*background:#fff;color:#171717/,
  'Follow-up form panels must use readable dark text');
assert.match(style, /input,textarea,select\\{[^}]*background:#fff;color:#171717/,
  'Follow-up form controls must use readable dark text');
assert.match(style, /\\.notice\\{[^}]*color:#171717/,
  'Follow-up notice panels must use readable dark text');
assert.match(style, /\\.alert\\{[^}]*color:#721c24/,
  'Follow-up alert panels must use readable dark warning text');
assert.match(style, /\\.small\\{[^}]*color:#62586a/,
  'Follow-up secondary text must remain readable on white panels');

const ids = [...html.matchAll(/\bid="([^"]+)"/g)].map(match => match[1]);
const domainIds = [
  'depression', 'anxiety', 'trauma', 'attention', 'moodEpisodes',
  'psychosis', 'substanceDomain', 'neurodevelopment', 'personality', 'sleepMedical',
];
for (const id of domainIds) {
  ids.push('evidence_' + id, 'status_' + id, 'diag_' + id, 'why_' + id);
}
function createHarness() {
  const elements = Object.fromEntries(ids.map(id => [id, {
    id,
    value: '',
    textContent: '',
    innerHTML: '',
    scrollIntoView() {},
  }]));
  const stored = new Map();
  let failWrites = false;
  const document = {
    getElementById(id) { return elements[id] || null; },
  };
  const localStorage = {
    getItem(key) { return stored.get(key) ?? null; },
    setItem(key, value) {
      if (failWrites) throw new Error('simulated storage failure');
      stored.set(key, value);
    },
    removeItem(key) { stored.delete(key); },
  };
  const sandbox = { document, localStorage };
  vm.runInNewContext(
    scripts[0] + '\nglobalThis.__followupTest = { state, collect, saveForm, loadForm, buildReport };',
    sandbox,
    { filename: 'prototype/follow-up-assessment.html' },
  );
  return {
    app: sandbox.__followupTest,
    elements,
    stored,
    set failWrites(value) { failWrites = value; },
  };
}

function run() {
  const h = createHarness();
  const { app, elements, stored } = h;

  elements.clientRef.value = 'SYNTHETIC-FOLLOWUP-001';
  elements.reviewDate.value = '2026-10-31';
  elements.clinician.value = 'Test Clinician';
  elements.timeline.value = '<b>Injected</b>';
  elements.currentRisk.value = 'No';

  app.saveForm();
  assert.ok(stored.has('stnFollowupAssessment'),
    'Follow-up form should save its structured state locally');
  assert.equal(elements.saveStatus.textContent.includes('Saved locally'), true,
    'Successful save should show a visible saved status');

  app.buildReport();
  assert.match(elements.reportOutput.innerHTML, /&lt;b&gt;Injected&lt;\/b&gt;/,
    'Follow-up report must escape user-entered HTML');
  assert.equal(elements.reportOutput.innerHTML.includes('<b>Injected</b>'), false,
    'Follow-up report must not render user-entered markup');

  elements.timeline.value = '';
  app.loadForm();
  assert.equal(elements.timeline.value, '<b>Injected</b>',
    'Saved follow-up form should restore the timeline field');

  h.failWrites = true;
  app.saveForm();
  assert.match(elements.saveStatus.textContent, /Local save failed/,
    'Storage failure should be visible and must not be reported as saved');

  console.log('PASS: follow-up form persistence, restore, report escaping and storage failure handling');
}

run();

#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const root = path.resolve(__dirname, '..');
const html = fs.readFileSync(path.join(root, 'prototype/index.html'), 'utf8');
const scripts = [...html.matchAll(/<script\\b[^>]*>([\\s\\S]*?)<\\/script\\s*>/gi)]
  .map(match => match[1].trim())
  .filter(Boolean);

assert.equal(scripts.length, 1, 'Prototype must contain exactly one inline application script');

const ids = [...html.matchAll(/\\bid="([^"]+)"/g)].map(match => match[1]);
const viewIds = [...html.matchAll(/<section id="([^"]+)"/g)].map(match => match[1]);

function createHarness() {
  const elements = Object.fromEntries(ids.map(id => [id, {
    id,
    value: '',
    textContent: '',
    innerHTML: '',
    style: {},
    classList: {
      active: false,
      add() { this.active = true; },
      remove() { this.active = false; },
    },
  }]));
  const stored = new Map();
  const alerts = [];
  let failWrites = false;

  const document = {
    getElementById(id) { return elements[id] || null; },
    querySelectorAll(selector) {
      return selector === '.view' ? viewIds.map(id => elements[id]) : [];
    },
  };
  const localStorage = {
    getItem(key) { return stored.get(key) ?? null; },
    setItem(key, value) {
      if (failWrites) throw new Error('simulated storage quota failure');
      stored.set(key, value);
    },
    removeItem(key) { stored.delete(key); },
  };
  const sandbox = {
    document,
    localStorage,
    alert(message) { alerts.push(String(message)); },
    confirm() { return true; },
    location: { reload() {}, assign() {} },
  };

  vm.runInNewContext(
    scripts[0] + '\nglobalThis.__stnTest = { A, show, saveClientAndContinue, setAnswer, setRisk, saveSafety, calculate, saveReview, saveCare, flags, saveData, renderReport };',
    sandbox,
    { filename: 'prototype/index.html' },
  );

  return {
    app: sandbox.__stnTest,
    elements,
    alerts,
    stored,
    set failWrites(value) { failWrites = value; },
  };
}

function run() {
  const h = createHarness();
  const { app, elements, alerts } = h;

  app.show('assessment');
  assert.equal(elements.assessment.classList.active, false,
    'Assessment must not be accessible before consent and client details');

  Object.assign(elements.clientId, { value: 'SYNTHETIC-001' });
  Object.assign(elements.clientName, { value: 'Synthetic Client' });
  Object.assign(elements.dob, { value: '1990-01-01' });
  Object.assign(elements.assessDate, { value: '2026-10-31' });
  Object.assign(elements.clinician, { value: 'Test Clinician' });
  Object.assign(elements.consent, { value: 'Yes' });
  app.saveClientAndContinue();
  assert.equal(elements.assessment.classList.active, true,
    'Saved client with confirmed consent should open screening');

  for (const id of [
    'mood', 'sleep', 'energy', 'worry', 'tension',
    'trauma', 'avoid', 'attention', 'function',
  ]) app.setAnswer(id, '0');

  app.show('safety');
  assert.equal(elements.safety.classList.active, true,
    'All answered screening items should permit the safety gate');

  app.calculate();
  assert.equal(elements.results.classList.active, false,
    'Results must remain blocked until the safety gate is saved');

  for (const id of [
    'suicide', 'selfharm', 'attempt', 'violence',
    'psychosis', 'mania', 'substance', 'danger',
  ]) app.setRisk(id, 'No');
  app.saveSafety();
  app.calculate();
  assert.equal(elements.results.classList.active, true,
    'Complete saved safety responses should permit results');
  assert.equal(app.flags().length, 0,
    'Negative safety responses must not create positive flags');

  elements.signoff.value = 'Test Clinician';
  app.saveReview();
  app.show('care');
  assert.equal(elements.care.classList.active, true,
    'Saved clinician review and sign-off should permit care planning');

  elements.goals.value = 'Synthetic goal';
  elements.plan.value = 'Synthetic support';
  app.saveCare();
  app.show('report');
  assert.equal(elements.report.classList.active, true,
    'Saved care plan should permit report viewing');

  app.A.review.mse = '<img src=x onerror=alert(1)>';
  app.renderReport();
  assert.match(elements.reportBox.innerHTML, /&lt;img/,
    'User-entered report text must be HTML-escaped');

  app.setRisk('suicide', 'Yes');
  assert.equal(app.A.safetySaved, false,
    'Changing a safety response must invalidate the saved safety gate');
  app.saveSafety();
  app.calculate();
  assert.deepEqual(Array.from(app.flags()), ['suicide'],
    'A positive response must be surfaced for clinician review');

  h.failWrites = true;
  assert.equal(app.saveData(), false,
    'Storage write failures must be caught and reported');
  assert.ok(alerts.some(message => message.includes('Browser storage failed')),
    'Storage write failure must show a visible warning');

  console.log('PASS: prototype workflow, consent, completion gates, safety flags, report escaping and storage failure handling');
}

run();

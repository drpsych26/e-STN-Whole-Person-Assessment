'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const sourcePath = path.join('reference', 'source-html', 'STN_Initial_Assessment_Paper_Pilot.html');
const registerPath = path.join('reference', 'traceability', 'STN-INITIAL-1.0.0-item-traceability.json');

function decodeEntities(value) {
  return value
    .replace(/&#(\d+);/g, (_, number) => String.fromCharCode(Number(number)))
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&#39;/g, "'");
}

function stripHtml(value) {
  return decodeEntities(
    value
      .replace(/<br\s*\\?\/?/gi, ' ')
      .replace(/<[^>]+>/g, ' ')
      .replace(/\s+/g, ' ')
      .trim(),
  );
}

function parsePaperPilot(html) {
  const sourceItems = [];
  const headings = [...html.matchAll(/<h2>([\s\S]*?)<\\/h2>([\s\S]*?)(?=<h2>|<\\/body>)/gi)];

  for (let headingIndex = 0; headingIndex < headings.length; headingIndex += 1) {
    const section = stripHtml(headings[headingIndex][1]);
    const table = headings[headingIndex][2].match(/<table class="qtable">([\s\S]*?)<\\/table>/i)?.[1];
    if (!table) continue;

    const headerRow = table.match(/<tr>([\s\S]*?)<\\/tr>/i)?.[1] ?? '';
    const responseHeaders = [...headerRow.matchAll(/<th[^>]*>([\s\S]*?)<\\/th>/gi)]
      .map((match) => stripHtml(match[1]))
      .filter((header) => header !== '#' && header !== 'Item');

    for (const row of table.matchAll(/<tr>([\s\S]*?)<\\/tr>/gi)) {
      const cells = [...row[1].matchAll(/<td[^>]*>([\s\S]*?)<\\/td>/gi)].map((match) => match[1]);
      if (cells.length < 2) continue;

      const itemNumber = stripHtml(cells[0]);
      if (!/^\d+$/.test(itemNumber)) continue;

      const safetyTags = [...cells[1].matchAll(/class=["']pill["'][^>]*>([\s\S]*?)<\\/span>/gi)]
        .map((match) => stripHtml(match[1]));

      sourceItems.push({
        trace_id: `STN-INITIAL-1.0.0-H${String(headingIndex + 1).padStart(2, '0')}-I${String(itemNumber).padStart(2, '0')}`,
        source_heading_ordinal: headingIndex + 1,
        source_section: section,
        source_item_number: Number(itemNumber),
        source_item_text: stripHtml(cells[1]),
        source_safety_tags: safetyTags,
        source_response_headers: responseHeaders,
      });
    }
  }

  return sourceItems;
}

const html = fs.readFileSync(sourcePath, 'utf8');
const register = JSON.parse(fs.readFileSync(registerPath, 'utf8'));
const sourceItems = parsePaperPilot(html);

assert.equal(sourceItems.length, 208, 'The paper-pilot source must yield exactly 208 table items.');
assert.equal(register.extraction.expected_item_count, 208);
assert.equal(register.items.length, 208, 'The traceability register must contain every source item exactly once.');

const byTraceId = new Map(register.items.map((item) => [item.trace_id, item]));
assert.equal(byTraceId.size, 208, 'Trace IDs must be unique.');

for (const sourceItem of sourceItems) {
  const registered = byTraceId.get(sourceItem.trace_id);
  assert.ok(registered, `Missing traceability row for ${sourceItem.trace_id}`);
  assert.deepEqual(
    {
      source_heading_ordinal: registered.source_heading_ordinal,
      source_section: registered.source_section,
      source_item_number: registered.source_item_number,
      source_item_text: registered.source_item_text,
      source_safety_tags: registered.source_safety_tags,
      source_response_headers: registered.source_response_headers,
    },
    sourceItem,
    `Source mismatch for ${sourceItem.trace_id}`,
  );
}

const partA = register.items.filter((item) => item.source_section.startsWith('Part A - Whole-Person Core Intake'));
assert.equal(partA.length, 25, 'Only the source Part A set has 25 mapped Flutter items.');
for (const item of partA) {
  assert.equal(item.implementation.scope, 'flutter_part_a');
  assert.match(item.implementation.ui_reference, /whole_person_initial_assessment_screen\.dart#core-item-\d+$/);
  assert.match(item.implementation.data_reference, /core_intake\.dart#coreIntakeQuestions\[\d+\]$/);
  assert.equal(item.controls.routing_or_scoring_status, 'NOT_INFERRED_OR_IMPLEMENTED_BY_THIS_REGISTER');
}

const nonPartA = register.items.filter((item) => !item.source_section.startsWith('Part A - Whole-Person Core Intake'));
assert.equal(nonPartA.length, 183);
for (const item of nonPartA) {
  assert.equal(item.implementation.scope, 'not_implemented');
  assert.equal(item.implementation.ui_reference, null);
  assert.equal(item.implementation.data_reference, null);
  assert.equal(item.implementation.validation_reference, null);
  assert.equal(item.implementation.reporting_reference, null);
}

console.log(`PASS: 208 source items match ${registerPath}; 25 Part A mappings and 183 non-implemented items are explicit.`);

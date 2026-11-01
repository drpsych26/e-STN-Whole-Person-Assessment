# STN source reconciliation inventory — 1 November 2026

**Disposition: PARTIAL INVENTORY COMPLETE — SOURCE IMPORT AND CLINICAL RECONCILIATION OPEN.**  
**Use boundary: private development; synthetic data only.**

This report records the files actually available in the current project workspace and the differences that can be established from those files. It does not certify that one version is clinically authoritative.

## 1. Supplied source inventory

SHA-256 values below were calculated from the exact files in the current workspace.

| Source file | Bytes | SHA-256 | Import to GitHub |
|---|---:|---|---|
| `STN_Initial_Assessment_Paper_Pilot.html` | 255,220 | `16c6470cd74d9d751d9474b3eb8d4c1f94a22200bcb92ce6c2524639d8d85aea` | Imported to `reference/source-html/`; UTF-8 byte length matches; raw SHA re-verification still required |
| `STN_Initial_Assessment_Paper_Pilot_v1.pdf` | 232,623 | `037e1554530a7734ff8e6e6cdc7e086a4a6a9120992c2e24d42512448d0c72c0` | OPEN — local source only |
| `stn-whole-person-assessment-v2.5.html` | 161,089 | `3b51c7a9292b74841df9a7c5f9356842f6710cb646e05b3df9f4740c01d5afca` | Text extraction imported; NOT byte-identical (134,803 UTF-8 bytes) |
| `stn-whole-person-assessment-v2.6.html` | 170,010 | `2b3bf1a18c4d02432839ed07a3edb0d68445fc0dd8a28a15d9db018d5f06826c` | Text extraction imported; NOT byte-identical (139,655 UTF-8 bytes) |
| `Supportive Therapy Network — Whole Person Initial Assessment.html` | 152,315 | `fac9b9c90bf4719294dd38d2ac99c70ca293c186e0a07f0da161e1651e185d22` | Text extraction imported; NOT byte-identical (133,050 UTF-8 bytes) |
| `Supportive Therapy Network — Whole Person Initial Assessment (2).html` | 166,318 | `491cef23d2cb957e7278045b1db98f3a76528de7a1e01fe2b46f6766b6f3b2a8` | Text extraction imported; NOT byte-identical (134,730 UTF-8 bytes) |
| `STN_Diagnostic_Tool_Flutter_MVP_Pack_v2.zip` | 9,428 | `79de9cdb2683ae3a5268f1ee83b3d5aff72d300bbdc6e1ad6c370e504de3deb6` | OPEN — local source only |
| `STN_Diagnostic_Tool_Flutter_MVP_Pack_v3.zip` | 12,684 | `ed9a11a25b52e8f40e3f8282b84385b9345d06cf333e2abf7e17b199eade57db` | OPEN — local source only |
| `STN_Diagnostic_Tool_Flutter_MVP_Pack_v4.zip` | 13,802 | `4478e3e54131fdb94db943524a7aa00cef9239122e572eaad6d9e0d5ad95261c` | PRESERVED in repository as base64 archive chunks |
| `STN_Diagnostic_Tool_Flutter_MVP_Coding_Pack.zip` | 5,152 | `d10f0d30cca71f8fe5e78bd3a72cd80e173b2eb33078d28ce46a7077fdb5571d` | OPEN — local source only |

The five HTML files now have text representations in `reference/source-html/`. Only the paper-pilot extraction has a UTF-8 byte length matching the mounted original; even that still needs an independently recomputed raw SHA-256 after import. The other four HTML extracts are shorter than their mounted originals and are not byte-identical. The PDF and Flutter v2/v3/coding ZIPs remain local only. The v4 archive is preserved in repository base64 chunks. This inventory is not a completed byte-for-byte source import.

## 1A. Import fidelity check

The five HTML uploads were read through the project file-text extraction service and committed as text. GitHub fetches were compared to the extracted text and matched character-for-character. The paper-pilot extracted text has the same UTF-8 byte length as the mounted original (255,220 bytes). The other four extracted HTML files are shorter than their mounted originals, so embedded content or formatting was omitted by extraction. They are useful for preliminary review and syntax checking only; they must not be represented as byte-identical originals. The original PDF and Flutter v2/v3/coding ZIPs have not been imported. The original files remain available in the project upload workspace.

## 2. Paper pilot content inventory

The supplied paper-pilot HTML identifies itself as:

- Title: STN Whole-Person Initial Assessment
- Version: `STN-INITIAL-1.0.0`
- Date: 24 August 2026
- Status: paper pilot / pre-production clinical decision-support material
- Explicit boundary: screens and structures information; does not establish a diagnosis; safety concerns require human assessment.

Its tables contain 208 items across 24 groups:

| Section | Items |
|---|---:|
| Part A — Whole-Person Core Intake | 25 |
| Part B1 — PHQ-9 | 9 |
| Part B2 — GAD-7 | 7 |
| Depression | 9 |
| Generalised Anxiety | 8 |
| Panic Symptoms | 6 |
| Trauma / PTSD Features | 9 |
| Bipolar-Spectrum Features | 9 |
| Psychosis-Spectrum Experiences | 8 |
| Obsessive-Compulsive Features | 7 |
| ADHD Features | 10 |
| Autism-Related Traits | 8 |
| Alcohol-Related Harm | 9 |
| Drug / Medication-Related Harm | 9 |
| Eating / Body-Image Concerns | 7 |
| Sleep Problems | 7 |
| Dissociation | 6 |
| Anger / Aggression | 7 |
| Grief / Bereavement | 7 |
| Personality / Relationship Patterns | 9 |
| Somatic / Health Anxiety | 6 |
| Suicide / Self-Harm Safety Assessment | 10 |
| Violence / Abuse / Safeguarding | 7 |
| Social / Practical Needs | 9 |
| **Total** | **208** |

The paper pilot also contains consent/privacy prompts, a response scale, a core routing/safety summary, final assessment summary, recommended next step and notes/referral handover.

## 3. Flutter archive scope differences

Inspection of the supplied ZIP manifests shows:

- v2 contains MDD, GAD, PTSD and ADHD modules with a basic scoring engine and results storage.
- v3 retains those four modules and adds OCD, bipolar and substance-use modules, secure local storage and report builder.
- v4 contains MDD, GAD, PTSD and ADHD modules, profile models, secure local Hive storage, scoring and report builder.
- The coding pack is a smaller MDD-oriented starter.

The v4 archive is not the 208-item Whole Person Initial Assessment. Its Flutter module MVP is not a complete implementation of the paper pilot.

## 4. Current repository implementation comparison

The current browser prototype contains 9 simplified screening questions and 8 safety prompts. The original Flutter v4 archive is a four-module MVP; draft PR #12 adds the paper pilot's 25 Part A core items to Flutter, with source-wording golden tests, synthetic-only storage/profile guards and interim human-review flags. The supplied paper pilot contains 208 items across 24 groups.

Therefore:
- Part A has a partial Flutter implementation in PR #12; its wording is checked against a golden test, but CI and independent clinical review remain pending;
- the browser prototype and Flutter MVP are not yet the full paper-pilot workflow;
- question wording, order, response scales, branching, scoring, safety flags and report outputs still require row-level reconciliation;
- no Clinical Core v2 canonical source file or signed approval is present in the supplied file inventory;
- no instrument permission register or written digital-use permission evidence has been supplied.

## 5. Conflicts and decisions that must not be guessed

1. Identify which of the paper-pilot, v2.5, v2.6 and two named HTML exports is the approved current initial-assessment source.
2. Identify the approved Clinical Core v2 version and its change history.
3. Confirm whether the PHQ-9 and GAD-7 digital reproduction, scoring, export and storage use is authorised for STN's intended deployment.
4. Resolve any differences between paper-pilot items, the later HTML builds and Flutter module prompts through an approved clinical change record.
5. Confirm whether the second-stage Clinical Follow-Up & Diagnostic Formulation Assessment is a separate product workflow or a later stage inside the same client record.

No source conflict has been silently reconciled in code.

## 6. Next source-fidelity acceptance gate

- Import every original file byte-for-byte into a versioned `reference_sources/` directory.
- Verify all imported hashes against this inventory.
- Extract every item ID, exact wording, response option, timeframe, safety tag, routing rule and report field into the traceability register.
- Map each source item to its UI component, data model, scoring/routing rule, report output and automated test.
- Record every discrepancy and obtain a dated clinical-owner decision.
- Have an independent clinical reviewer verify the traceability and golden test vectors.

**Current result: inventory and discrepancy identification completed from the available local files; source import, authoritative-version approval, full traceability and clinical validation remain OPEN/BLOCKED.**

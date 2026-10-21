# Pre-release verification audit — 22 October 2026

Status: PRIVATE REVIEW ONLY. Do not publish or deploy.

## Verified in the current workspace

| Asset | Bytes | SHA-256 | Result |
|---|---:|---|---|
| `stn-whole-person-assessment-v2.6.html` | 170010 | `2b3bf1a18c4d02432839ed07a3edb0d68445fc0dd8a28a15d9db018d5f06826c` | File hash recorded; static inspection only |
| `stn-whole-person-assessment-v2.5.html` | 161089 | `3b51c7a9292b74841df9a7c5f9356842f6710cb646e05b3df9f4740c01d5afca` | Historical comparison copy |
| `STN_Initial_Assessment_Paper_Pilot.html` | 255220 | `16c6470cd74d9d751d9474b3eb8d4c1f94a22200bcb92ce6c2524639d8d85aea` | File hash recorded; static inspection only |
| Flutter MVP v2 ZIP | 9428 | `79de9cdb2683ae3a5268f1ee83b3d5aff72d300bbdc6e1ad6c370e504de3deb6` | ZIP integrity passed; 13 entries |
| Flutter MVP v3 ZIP | 12684 | `ed9a11a25b52e8f40e3f8282b84385b9345d06cf333e2abf7e17b199eade57db` | ZIP integrity passed; 18 entries |
| Flutter MVP v4 ZIP | 13802 | `4478e3e54131fdb94db943524a7aa00cef9239122e572eaad6d9e0d5ad95261c` | ZIP integrity passed; 17 entries |
| Flutter coding pack ZIP | 5152 | `d10f0d30cca71f8fe5e78bd3a72cd80e173b2eb33078d28ce46a7077fdb5571d` | ZIP integrity passed; 8 entries |

## Static findings requiring follow-up

1. Both v2.5 and v2.6 HTML files reference `/runtime-config.js`. Hosting must provide this file or the dependency must be safely resolved without changing approved behaviour.
2. Both HTML files reference Google Fonts assets and `manifest.webmanifest`; offline behavior and missing-manifest behavior need testing.
3. v2.6 contains 26 button elements versus 16 in v2.5. This is a version difference, not proof of correctness. Compare behaviour and wording before choosing any source.
4. The paper-pilot HTML is static (no script tags, forms, or buttons detected), consistent with a printable/paper-oriented artifact; visual/manual review is still required.
5. ZIP integrity passed for all four Flutter packs. This does not prove the Dart project compiles, that dependencies resolve, or that any clinical workflow works.

## Required product acceptance baseline

Preserve the Clinical Core v2 workflow:

Dashboard → New Client → Whole Person Initial Assessment → Safety Gate → Adaptive Routing → Selected Assessments → Integrated Results → Clinical Review → Diagnostic Decision Support → Whole-Person Care Plan → Finalise → Report.

Mandatory requirements to verify:
- Role-based authentication and least-privilege access; MFA where appropriate.
- Clinically relevant audit trail and controlled record correction/addendum.
- Schema validation, per-question scales, versioned scoring and licensed instrument cut-offs.
- Safety endorsements and uncertain responses trigger a human-led follow-up path; total scores must never be used to infer safety.
- Clear separation of client-reported answers, automated calculations and clinician interpretation.
- No autonomous diagnosis or autonomous crisis decision-making.
- Privacy impact assessment, consent, minimisation, retention/deletion, encryption, incident response and vendor review.
- Offline/low-bandwidth behavior, secure local storage, sync conflict and restore tests.
- Accessible phone/tablet layout, report/print behavior and workflow regression tests.
- Pilot protocol, clinical sign-off, instrument licensing review, adverse-impact/equity review and incident procedures.

## Current verification boundary

This audit is a static file inventory and archive-integrity check. It is not a browser end-to-end test, Flutter build, clinical validation, penetration test, legal compliance opinion, or deployment approval. No live deployment or publication is authorised by this document. Keep all testing on synthetic data until the relevant privacy and clinical governance gates pass.

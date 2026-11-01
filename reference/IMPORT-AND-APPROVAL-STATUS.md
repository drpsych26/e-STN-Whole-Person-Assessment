# STN source import and approval status

## Source-of-truth rule
The supplied STN Whole Person Initial Assessment HTML and paper-pilot HTML are the authoritative clinical/content references. Any app implementation must preserve their wording, questions, response options, scoring, flags, routing, and reporting behaviour unless an explicitly approved change is documented.

## Current import status — 31 October 2026
- The supplied Flutter v4 archive is preserved in `flutter/source-archives/parts/` and reconstructed in CI with an expected SHA-256 check.
- Tracked Flutter remediation patches and tests are stored under `implementation-patches/flutter-v4/`.
- Five HTML source text-extracts are present in `reference/source-html/`; four are shorter than the uploaded originals and are not byte-identical. The PDF and Flutter v2/v3/coding ZIPs remain local and are not imported. See the source reconciliation inventory for byte counts and hashes.
- The browser prototype and Flutter v4 module MVP have not been demonstrated to be exact matches for the approved paper pilot or Clinical Core v2.

## Approval boundary
Project-owner approval authorises importing and implementing the same supplied materials. It does not constitute independent clinical validation, instrument licensing, regulatory approval, or approval for real-client deployment.

## Verification gate
Do not mark the digital implementation as an exact match until all original HTML files and Flutter packs are committed, their content is compared against the implementation, question-by-question traceability is reviewed, and all assessment paths are regression-tested. Keep the repository private and use synthetic data only.

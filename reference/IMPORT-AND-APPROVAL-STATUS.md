# STN source import and approval status

## Source-of-truth rule
The supplied STN Whole Person Initial Assessment HTML and paper-pilot HTML are the authoritative clinical/content references. Any app implementation must preserve their wording, questions, response options, scoring, flags, routing, and reporting behaviour unless an explicitly approved change is documented.

## Approval boundary
Project-owner approval authorises importing and implementing the same supplied materials. It does not constitute independent clinical validation, regulatory approval, or approval for real-client deployment.

## Verification gate
Do not mark the digital implementation as an exact match until the original HTML files and Flutter packs are committed, their content is compared against the implementation, and the assessment paths are regression-tested. Keep the repository private and do not use real client data in the prototype.

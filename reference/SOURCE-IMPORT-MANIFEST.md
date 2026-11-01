# STN source import manifest and verification gates

The original uploads were inventoried in the current project workspace on 1 November 2026. The full inventory and SHA-256 hashes are recorded in `reference/SOURCE-RECONCILIATION-INVENTORY-2026-11-01.md`. The five HTML sources have text-extracted representations in `reference/source-html/`; four are not byte-identical to their uploaded originals. The PDF and Flutter v2/v3/coding ZIPs remain local. The Flutter v4 archive is preserved as base64 chunks. Do not treat the HTML text imports as byte-identical originals.

| Source asset | Bytes | SHA-256 prefix |
|---|---:|---|
| `prototype/index.html` | 13,935 | `cc64f17ad7e9f45f` |
| `flutter/STN_Diagnostic_Tool_Flutter_MVP_Coding_Pack.zip` | 5,152 | `d10f0d30cca71f8f` |
| `flutter/STN_Diagnostic_Tool_Flutter_MVP_Pack_v4.zip` | 13,802 | `4478e3e54131fdb9` |
| `reference/stn-whole-person-assessment-v2.6.html` | 170,010 | `2b3bf1a18c4d0243` |
| `reference/STN_Initial_Assessment_Paper_Pilot.html` | 255,220 | `16c6470cd74d9d75` |
| `reference/PRODUCTION-NZ-REQUIREMENTS.md` | 1,719 | `5e2348b40b1baad6` |
| `reference/DEPLOYMENT-CHECKLIST.md` | 2,238 | `7b1ce3a6cb97de83` |
| `reference/MASTER_SPEC.md` | 1,897 | `ad3fbe4a055e92ba` |
| `SECURITY.md` | 543 | `221fb46c0dd17fe8` |
| `.gitignore` | 252 | `5a8a9a1b03753693` |
| `README.md` | 2,363 | `6b237755bb29a8f6` |

## Mandatory verification before calling the implementation exact-match
1. Commit the original HTML sources and both Flutter ZIP assets without modifying them.
2. Compare implemented assessment questions, options, order, scoring, safety logic, routing and reports against the original source files.
3. Run build/static checks and manual tests for phone/tablet layouts, offline behaviour, navigation, data persistence, export/print, and failure states.
4. Keep demo and real-client environments separate. Production requires approved authentication, secure backend storage, audit logging, privacy and clinical governance review.

## Status
The bundle has been inspected locally, but the manifest alone is not evidence that every listed file has been imported to GitHub or that the app has passed exact-match testing. Do not claim complete import or production readiness until those gates are evidenced.
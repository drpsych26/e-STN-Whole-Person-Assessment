# Imported Flutter v4 source archive

The original uploaded archive is preserved as base64 text at:

- `parts/part1.txt`, `parts/part2.txt` and `parts/part4.txt`

This encoding preserves the original ZIP bytes. The SHA-256 of the decoded ZIP must equal:

`4478e3e54131fdb94db943524a7aa00cef9239122e572eaad6d9e0d5ad95261c`

The GitHub Actions workflow concatenates these chunks, verifies the exact encoded length and decoded SHA-256, then extracts the archive into `flutter/source/`, applies the tracked conservative scoring-engine replacement and UI/report wording patch, and then runs the pinned Flutter formatter, analyzer, unit tests and Android debug build.

The original archive remains unchanged. The patches are maintained separately under `implementation-patches/flutter-v4/`.

**Boundary:** This is a development MVP. Encrypted local storage is not authentication, server-side authorisation, multi-user clinical record security or an approved production data architecture. The module questions are not established as licensed/validated instruments. Do not enter real client data or use for clinical decisions. Release remains HOLD pending all clinical, privacy, security and governance gates.

## Chunk numbering

The chunks are numbered `part1`, `part2` and `part4`. There is no `part3`. This is deliberate: the numbering comes from the original export, and no chunk was removed or renamed during import. The CI workflow concatenates the three files in order and verifies the exact encoded length and the decoded SHA-256 above, so any missing or altered chunk fails the build. Do not add or renumber chunks without re-verifying that hash.

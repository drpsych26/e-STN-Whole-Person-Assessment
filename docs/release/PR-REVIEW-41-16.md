# Review of open PRs #41 and #16 for release-path dependencies

Neither PR has been merged. Neither should be merged until its own review is complete.

## PR #41: Harden Android testing releases and correct clinical evidence status
- Branch: `release/harden-testing-apk-and-dossier` into `main`. Last updated 16 November 2026.
- Files: `.github/workflows/android-apk.yml`, `docs/governance/CLINICAL-RELEASE-DOSSIER.md`, `docs/release/PRODUCTION-GO-LIVE-GATE.md`.
- **Release-path dependency: yes.** It edits the APK workflow that CI depends on, and it edits the go-live gate document, which governs release status. A change to the gate document must not weaken any gate. This needs a line-by-line comparison against the current gate register before merge.
- Mergeable state from GitHub: `unknown`. CI status not confirmed.

## PR #16: Release candidate: STN branding, typography and copyright polish
- Branch: `release/brand-copyright-polish-2026-11-04` into `main`. Last updated 5 November 2026.
- Files: `README.md`, `assets/brand/stn-mark.svg`, `docs/brand/STN-BRAND-AND-INTERFACE-STANDARD.md`, `docs/release/RELEASE-PREPARATION-2026-11-04.md`, `implementation-patches/flutter-v4/lib/main.dart`, `implementation-patches/flutter-v4/lib/screens/home_screen.dart`, `implementation-patches/flutter-v4/patch_ui.py`, `prototype/index.html`.
- **Release-path dependency: yes.** It changes the Flutter UI entry point and the prototype landing page. It also introduces a new mark (`stn-mark.svg`), which conflicts with the brand lock in the handoff notes: the approved logo is the original PNG, used unchanged.
- It is five months old relative to the current branch and predates PR #51 and the release gate work. It will conflict with `main`.
- **Recommendation:** do not merge. Rebase or recreate on the current branch after the brand question is settled.

## Decision requested
1. Close PR #16 pending a brand decision that preserves the original logo.
2. Review PR #41 against the gate register before any merge.

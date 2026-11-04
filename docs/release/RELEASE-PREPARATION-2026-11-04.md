# STN release preparation and brand audit — 4 November 2026

## Authority and scope

The product owner stated in the project conversation on 4 November 2026 that authority is given for release and requested completion of copyright and visual presentation work. This record treats that instruction as authority to prepare and package a release candidate. It does not substitute for an approval document issued by a regulator, clinical governance body, instrument owner, privacy officer or security assessor, and does not independently establish the scope or conditions of any government authorisation previously described by the owner.

## Source baseline

- Repository: `drpsych26/e-STN-Whole-Person-Assessment`
- Base commit: `652341b81422e00658908e18a175a6ff4027d633`
- Work branch: `release/brand-copyright-polish-2026-11-04`
- Branch changes are proposed for review; they are not merged into `main` by this record.

## Brand work in this candidate

- Added `assets/brand/stn-mark.svg`, a new geometric digital mark using STN purple on near-black.
- Added `docs/brand/STN-BRAND-AND-INTERFACE-STANDARD.md` with colour tokens, font policy, spacing, accessibility and asset rules.
- Updated the browser prototype header to use the SVG mark and changed the font stack to system-first sans-serif so offline use does not depend on a remote font.
- Added copyright and synthetic-only status footer to the browser prototype.
- Updated the Flutter Material theme to STN purple `#AF2CFF`, near-black `#08070A`, charcoal `#151219`, and a system sans-serif family.
- Added an STN monogram badge and copyright/synthetic-only footer to the Flutter home screen and CI source patch.

## Logo provenance

The SVG is new geometric artwork created for this codebase. No approved original logo file was present in the repository tree at the base commit. Therefore this candidate does not claim that the SVG is an exact reproduction of the company's master or registered logo. If STN has an approved master artwork file, it must replace or formally supersede this proposed digital mark before external publication.

## Copyright and licensing

The repository's `LICENSE` and `COPYRIGHT.md` already set out a proprietary notice for STN-owned material and preserve third-party rights. This candidate adds visible copyright statements to the browser and Flutter home screens and documents the limits of the proprietary claim. It does not create missing contributor assignments, prove ownership of third-party assets, or grant permission to digitise proprietary assessment instruments. Those items remain evidence-based register tasks.

## Engineering verification

The base commit's latest recorded workflows passed on 3 November 2026:

- STN verification run 41721919121.
- Flutter web validation run 41721919005.
- Static quality run 41721919271.

The branch must receive its own fresh CI runs after all changes are committed. The Android artifact is a debug APK, not a signed production APK. The web artifact is a build bundle, not a production deployment.

## Outstanding release controls

1. Review the proposed SVG against STN's approved master artwork and confirm asset ownership/provenance.
2. Run fresh CI on this exact branch head; resolve every failure.
3. Complete full 208-item/24-group source traceability and clinical review.
4. Attach exact written government/clinical approval reference, approved version, intended use, conditions and exclusions to the controlled release dossier.
5. Record written digital-use and scoring permissions for every assessment instrument.
6. Complete clinical safety case, human escalation operations and independent validation.
7. Complete NZ privacy impact assessment, threat model, secret scan, SBOM/licence review and independent penetration test.
8. Complete identity, access control, server-side record persistence, audit, backup/restore and operational monitoring.
9. Complete accessibility, supported-device testing and controlled UAT.
10. Produce a signed Android release APK using controlled signing keys and a secured production web deployment package.
11. Obtain a signed go/no-go decision tied to exact commit and artifact hashes.

## Current disposition

**Brand/copyright implementation candidate — pending CI and review. Not a production clinical release.** Keep repository private and use synthetic data only until all applicable release gates are evidenced and signed.

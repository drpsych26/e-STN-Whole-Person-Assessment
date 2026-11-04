# STN brand identity and visual-fidelity control

**Status:** Controlled implementation specification  
**Owner:** Supportive Therapy Network Limited (STN)  
**Effective review date:** 4 November 2026  
**Source of truth:** Owner-supplied STN logo and website / assessment reference images in the project record, plus the approved v2.6 HTML source.

## Non-negotiable identity

Use the supplied STN artwork as-is. Do not redraw, regenerate, trace, recolour, crop into a different composition, substitute, or approximate the brain mark or wordmark.

The approved identity shown in the supplied references is:
- Purple line-art human head / brain symbol.
- Black logo field / background.
- White serif wordmark: **SUPPORTIVE THERAPY NETWORK LTD**.
- White, letter-spaced tagline: **REHAB · RIGHT**.
- Purple brand accent on a near-black website background, with white primary headings and restrained lavender secondary text.

The reference palette records purple accent `#AF2CFF`. Preserve the supplied artwork's own pixel colours rather than recolouring the logo to match a CSS token.

## Canonical logo source and integrity

The full logo artwork is embedded as `LOGO_FULL_DATAURI` in the supplied source HTML under `reference/source-html/`. That embedded artwork is the current source reference; it is not permission to replace it with a newly generated asset.

**Outstanding asset-control task:** extract the embedded PNG byte-for-byte into a dedicated asset path, record its SHA-256, dimensions, file type, source HTML path and extraction method, then verify every website/app use against that hash. Do not claim this extraction or cross-product verification is complete until the evidence is committed.

Until that task is completed:
- Keep the original embedded artwork intact in the source HTML.
- Do not introduce a different logo file or a text-only substitute.
- Keep logo aspect ratio; use contain-style sizing and no distortion.
- Use the same artwork for header and hero placements. Scaling may differ; artwork must not.
- Do not place a purple glow, gradient, filter, mask or other effect over the logo artwork itself.

## Product-specific presentation

### Public website
Preserve the supplied website reference: dark/near-black canvas, purple accent, white high-contrast headline, restrained lavender navigation and copy, and the original STN logo. Preserve the wording and information architecture in the approved reference, including:
- “Support that sees the whole person.”
- Services, Our approach, Safety and Contact navigation.
- Human-led support and whole-person framing.
- Explicit development-stage / service-availability qualifications until service operations are verified.

### Clinical assessment application
The assessment product must remain recognisably STN-branded without sacrificing clinical usability:
- Use the original logo artwork without modification.
- Keep question wording, response scales, order, branching, safety content and clinical workflow controlled by the approved source specification—not by visual redesign.
- Maintain legible contrast, keyboard focus, responsive layouts and accessible control states.
- Keep decoration subordinate to clinical content. Do not use colour alone to communicate risk or clinical status.
- Any departure from the supplied approved v2.6 HTML must be recorded and accepted through version control; do not silently simplify or substitute screens.

## Fidelity acceptance checks

A release candidate is not an exact visual match until all of these are evidenced:
1. The canonical logo asset is extracted from the approved source and SHA-256 recorded.
2. Header, hero, app login/dashboard and report placements use the same canonical asset.
3. Logo aspect ratio, colour, wordmark, tagline, clear space and legibility match the supplied reference.
4. Website sections and approved UI labels are compared against the owner-supplied screenshots and source HTML.
5. Phone, tablet and desktop screenshots are reviewed at documented viewport sizes.
6. Automated visual regression checks cover critical screens; any accepted difference is recorded.
7. No clinical content, questions, scoring, safety rules or routing changed as part of a branding-only update.

## Rights and usage boundary

This brand specification records the intended identity; it does not establish who legally owns the logo, whether a trademark is registered, or whether any contributor has assigned rights to STN. Those matters remain governed by `docs/legal/IP-AND-LICENSING-REGISTER.md` and signed evidence held in restricted company records.

Do not publish or sublicense the logo or other STN-owned materials under an open-source licence unless STN has separately approved that grant in writing. Third-party fonts, icons, imagery and software retain their own licence terms.

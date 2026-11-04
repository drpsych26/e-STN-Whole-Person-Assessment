# STN brand and interface standard

**Product:** Supportive Therapy Network — Whole Person Assessment  
**Status:** Proposed repository master standard, 4 November 2026. Confirm against the company's approved master logo artwork before external publication.

## Brand direction

Use a restrained, high-contrast identity: STN purple on near-black for the corporate identity; neutral charcoal, white and greys for clinical assessment surfaces. Purple is an identity accent, not a clinical severity indicator. Do not use colour alone to communicate safety or clinical meaning.

## Colour tokens

| Token | Hex | Use |
|---|---|---|
| STN purple | `#AF2CFF` | Brand accent, active navigation, focus accents |
| Near black | `#08070A` | Brand/header background |
| Charcoal | `#151219` | Primary dark surface |
| Deep panel | `#1C1720` | Secondary dark surface |
| Border | `#382941` | Dark-surface borders |
| White | `#FFFFFF` | Primary text / light surfaces |
| Muted grey | `#C9C1D0` | Secondary text on dark |
| Alert red | `#B42332` | Alert state only, paired with text and icon |

Clinical assessment forms must remain neutral and readable. Ensure WCAG 2.2 AA contrast for text, controls, focus states and error states; validate actual rendered combinations rather than relying on token names.

## Typography

Use a system-first sans-serif stack for reliable offline rendering and consistent Android/Linux/macOS fallback:

`Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`

No remote font request is required. Do not describe Manrope or Inter as bundled unless font files and their licences are actually committed. Use a clear hierarchy: page title 1.25–1.5rem, section headings 1.1–1.25rem, body 1rem minimum, labels semibold. Keep line-height around 1.5 for body copy.

## Logo and clear space

`assets/brand/stn-mark.svg` is a newly added geometric STN pathway mark for this repository build. It is a proposed digital mark, not evidence that the company's previously approved master logo has been supplied or reproduced exactly. Use it on dark backgrounds, preserve its aspect ratio, and maintain clear space of at least one-quarter of its width. Do not stretch, recolour, add effects, or place it on visually noisy backgrounds. Replace it with the approved master artwork if the company has a different registered/approved logo.

## Layout and interaction

- Use consistent 8px spacing increments, 8–12px control radii and a 1050px desktop content maximum.
- Minimum touch target: 44×44 CSS px.
- Keep focus visible, keyboard navigation functional and reduced-motion preferences respected.
- Use text labels with every icon-only control; never rely on colour alone.
- Print reports on a white background with dark text and no navigation controls.
- Maintain New Zealand English (`en-NZ`) and consistent date formats.

## Copyright and third-party assets

STN-owned original artwork and interface source are proprietary only to the extent STN owns the rights. The SVG in this repository is newly authored for this implementation. Third-party fonts, libraries, icons, imagery and assessment instruments retain their own licence/permission terms. Preserve notices and record licences in the IP register. Do not use assessment instrument wording or scoring without documented permission.

## Release asset checks

Before external distribution, verify the approved logo source, asset provenance, licence inventory, colour contrast, font rendering on supported devices, SVG sanitisation, mobile layout, print output and copyright footer. Record evidence against the exact release commit and artifact hashes.

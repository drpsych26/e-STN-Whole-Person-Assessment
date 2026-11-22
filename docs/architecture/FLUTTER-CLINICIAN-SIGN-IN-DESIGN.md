# Flutter clinician sign-in — design note

**Status: design only; not implemented.** This note covers connecting the Flutter app (`implementation-patches/flutter-v4`) to the STN API's clinician sign-in and review workflow (PR #54). It was written instead of code because a correct mobile OIDC integration needs a native plugin and Android build changes. The app's source is restored from an archive and its `pubspec.yaml` and Android project are generated in CI, so those changes can only be built and tested in CI. Doing it properly is a separate, reviewable piece of work.

## 1. Principles

- **Default off.** Builds without the flag stay exactly as today: offline, synthetic-data demo, local encrypted storage, no network calls. Existing tests must pass unchanged.
- **System browser plus PKCE.** Sign-in uses the OS browser through AppAuth (authorisation code flow with PKCE). The app never collects passwords; the resource-owner password grant is not used.
- **The identity provider enforces MFA.** On Microsoft Entra ID, MFA is required through Conditional Access, and the API additionally rejects tokens without MFA evidence (PR #54).
- **The server is authoritative.** Roles come from the verified token and are enforced by the API. UI hiding is convenience, not authorisation. Offline drafts remain non-authoritative until submitted to the API.
- **Minimal token exposure.** Tokens are kept only in `flutter_secure_storage` (already used by the app) and are never logged. Sign-out clears them.

## 2. Build-time configuration (`--dart-define`)

| Key | Default | Purpose |
|---|---|---|
| `STN_API_ENABLED` | `false` | Master switch. `false` = current offline demo |
| `STN_API_BASE_URL` | empty | HTTPS base URL of the STN API |
| `STN_OIDC_ISSUER` | empty | Tenant issuer / discovery base |
| `STN_OIDC_CLIENT_ID` | empty | Public client id of the mobile app registration |
| `STN_OIDC_REDIRECT_URI` | `network.supportivetherapy.app:/oauth2redirect` | Custom-scheme redirect matching the Android application id |
| `STN_OIDC_SCOPES` | `openid profile offline_access api://<api-app-id>/access` | API scope set by the owner |

If `STN_API_ENABLED=true` but any value is missing, the app shows "Clinician sign-in is not configured in this build" and stays in demo mode (fail closed).

## 3. Components

1. `lib/config/api_config.dart`: reads the dart-defines and validates them (HTTPS only).
2. `lib/auth/auth_service.dart`: wraps `flutter_appauth` (pub.dev latest 13.0.0 at the time of writing; requires Flutter ≥ 3.44, which is compatible with the pinned 3.47.9) for sign-in, silent refresh and sign-out. It stores tokens through `flutter_secure_storage`.
3. `lib/api/stn_api_client.dart`: uses `package:http` (latest 1.6.0). It attaches the bearer token, maps 401 to re-authentication, 403 to "not permitted for your role or MFA", 404 to "not found", 409 to a workflow conflict message and 503 to "service unavailable". It sends no clinical data in URLs or logs.
4. `lib/screens/sign_in_screen.dart`: STN-branded (original logo, Manrope / Source Serif 4, purple #AF2CFF on #08070A). Shows the account, the effective roles from `GET /v1/me/access`, and MFA status.
5. Review screens, for reviewers only: a queue (`GET /v1/review-queue`), safety-flag acknowledgement, start review, return with reason, and sign-off quoting the content hash shown on screen.
6. Home screen: a "Clinician sign-in" entry, visible only when `STN_API_ENABLED=true`.

## 4. Build pipeline changes (needed to implement)

- Append `flutter_appauth` and `http` to the generated `pubspec.yaml` with the same guarded fragment approach used for fonts (`brand-pubspec-fonts.yaml`, PR #53).
- Android: add `manifestPlaceholders["appAuthRedirectScheme"] = "network.supportivetherapy.app"` in `implementation-patches/flutter-v4/android/app/build.gradle.kts`. Keep the existing release-signing rules unchanged.
- Workflows: the verification and Flutter web validation jobs build with the default (flag off). Add one job that builds with `STN_API_ENABLED=true` and dummy, non-secret configuration to prove compilation. Do not add real tenant values to the repository.

## 5. Tests

- Default build: the existing widget and unit tests pass with no changes, and the sign-in entry is absent.
- Config validation: missing or non-HTTPS values keep the app in demo mode.
- API client: status mapping and token header, tested with a fake HTTP client and synthetic responses.
- Auth service: sign-in, refresh and sign-out against a fake AppAuth implementation; tokens are cleared on sign-out.
- Review screens: sign-off is disabled until the displayed hash is confirmed, and flags must be acknowledged before review starts. Server errors are surfaced, not hidden.

## 6. Owner prerequisites

An STN-controlled Entra ID tenant; app registrations for the API (exposing the scope and app roles `STN.Clinician`, `STN.Reviewer`, `STN.Admin`) and for the mobile public client (redirect URI above); a Conditional Access policy requiring MFA; and a deployed non-production API with a managed database, holding synthetic data only. None of this exists yet (see the owner-only actions in `docs/release/PRODUCTION-GO-LIVE-GATE.md`).

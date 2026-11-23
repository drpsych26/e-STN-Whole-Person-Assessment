# Flutter clinician sign-in — design note

**Status: implemented on branch `flutter-clinician-signin` for engineering review; off by default; synthetic data only.** Section 7 records what was built and where it differs from this design. Nothing here connects to a real identity provider or API: no tenant values are in the repository, and a build only signs in when the owner supplies them.
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


## 7. Implementation (November 2026)

**Build variants instead of one build with a runtime switch.** `implementation-patches/flutter-v4/apply_clinician_api.py` applies the code in one of two variants:

- **default** (web validation, the verification debug APK, and the Android release unless requested): copies the API layer (`lib/api/`), the clinician screens (`lib/screens/clinician/`) and their tests. The platform files `lib/api/oidc_platform.dart` and `lib/api/transport_platform.dart` are offline stubs. `pubspec.yaml` and `AndroidManifest.xml` are not changed: no `flutter_appauth`, no `http`, no AppAuth redirect activity and no INTERNET permission. With `STN_API_ENABLED` off (the default), the home screen shows no sign-in entry. The Dart files are compiled in, but nothing reaches them. A CI step checks that the default APK has no AppAuth redirect activity. This variant is behaviour-identical to the earlier offline demo, though not byte-identical.
- **api** (the `flutter-clinician-api-variant` verification job, or the Android release workflow with `clinician_api: true`): additionally swaps in `api_variant/oidc_platform.dart` (flutter_appauth 13, authorisation code + PKCE in the system browser) and `api_variant/transport_platform.dart` (package:http 1.6; https only, redirects not followed, 30 s timeout). It adds both packages to `pubspec.yaml`, sets the redirect scheme `network.supportivetherapy.app` via `manifestPlaceholders`, and adds the INTERNET permission. CI builds this variant natively with synthetic placeholder values and checks the APK manifest for the redirect activity, the scheme and the permission.

This keeps a native sign-in plugin and its exported redirect activity out of every build that does not need them.

**Components as built** (names differ slightly from section 3):

| Design (section 3) | Implemented as |
|---|---|
| `lib/config/api_config.dart` | `lib/api/api_config.dart`: dart-defines, HTTPS-only validation, `problems` list, encoded path building |
| `lib/auth/auth_service.dart` | `lib/api/auth_service.dart` over an `OidcAdapter` interface (`lib/api/oidc.dart`); tokens in `lib/api/token_store.dart` (`flutter_secure_storage`, already a dependency); refresh 60 s before expiry; a failed refresh clears tokens; sign-out clears local tokens before calling the provider |
| `lib/api/stn_api_client.dart` | `lib/api/api_client.dart` over an `ApiTransport` interface (`lib/api/transport.dart`); maps 401, 403, 404, 409, 410 and 429 (with `Retry-After`); never puts tokens in messages |
| `lib/screens/sign_in_screen.dart` | `lib/screens/clinician/clinician_sign_in_screen.dart` and `clinician_home_screen.dart` (subject, organisation, roles and MFA from `GET /v1/me/access`) |
| Review screens | `review_queue_screen.dart` and `record_detail_screen.dart`: safety-flag acknowledgement (with the "not a risk assessment" confirmation), submit, start review (disabled until every flag is acknowledged), return with reason, and sign-off quoting the content hash |
| Home entry | `home_screen.dart`: "Clinician sign-in" card only when `STN_API_ENABLED=true`; "Not configured in this build" when values are missing |

**Tests** (`test/clinician_api_test.dart`, `test/clinician_screens_test.dart`, run in both variants):
- configuration validation and path encoding;
- client requests, headers and bodies, error mapping, and refusal when not configured;
- token storage, refresh and sign-out;
- the offline stubs;
- widget tests showing the entry absent when the flag is off and present when it is on;
- the "not configured" path;
- a full reviewer flow against a synthetic in-memory API: sign in, queue, acknowledge flag, start review, sign off.

The existing tests are unchanged.

**Not verified here:** sign-in against a real identity provider, refresh-token behaviour of a specific tenant, iOS (no iOS project is generated), and the release APK with `clinician_api: true`. That run needs the owner's signing secrets and the repository variables `STN_API_BASE_URL`, `STN_OIDC_ISSUER` and `STN_OIDC_CLIENT_ID` (and optionally `STN_OIDC_SCOPES`, which must include the API scope set by the owner).

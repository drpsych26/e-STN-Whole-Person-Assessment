// Default (offline) build: no sign-in plugin.
// The clinician API build variant replaces this file with
// implementation-patches/flutter-v4/api_variant/oidc_platform.dart
// (flutter_appauth). See apply_clinician_api.py.
import "oidc.dart";

OidcAdapter createPlatformOidcAdapter() => const UnavailableOidcAdapter();

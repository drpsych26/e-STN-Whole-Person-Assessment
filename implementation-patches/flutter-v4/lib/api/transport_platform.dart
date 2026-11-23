// Default (offline) build: no network transport.
// The clinician API build variant replaces this file with
// implementation-patches/flutter-v4/api_variant/transport_platform.dart
// (package:http). See apply_clinician_api.py.
import "transport.dart";

ApiTransport createPlatformTransport() => const UnavailableTransport();

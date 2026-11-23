/// Build-time configuration for the optional clinician API connection.
///
/// Values come from `--dart-define`. With STN_API_ENABLED false (the default)
/// the app is the offline, synthetic-data demo: no sign-in entry, no network
/// calls. With the flag on but any value missing or not HTTPS, sign-in stays
/// disabled and the app explains why (fail closed).
/// See docs/architecture/FLUTTER-CLINICIAN-SIGN-IN-DESIGN.md.
class ApiConfig {
  const ApiConfig({
    required this.enabled,
    required this.baseUrl,
    required this.issuer,
    required this.clientId,
    required this.redirectUri,
    required this.scopes,
  });

  /// Reads the build's dart-defines.
  const ApiConfig.fromEnvironment()
      : enabled = const bool.fromEnvironment("STN_API_ENABLED"),
        baseUrl = const String.fromEnvironment("STN_API_BASE_URL"),
        issuer = const String.fromEnvironment("STN_OIDC_ISSUER"),
        clientId = const String.fromEnvironment("STN_OIDC_CLIENT_ID"),
        redirectUri = const String.fromEnvironment(
          "STN_OIDC_REDIRECT_URI",
          defaultValue: defaultRedirectUri,
        ),
        scopes = const String.fromEnvironment(
          "STN_OIDC_SCOPES",
          defaultValue: "openid profile offline_access",
        );

  static const String redirectScheme = "network.supportivetherapy.app";
  static const String defaultRedirectUri = "$redirectScheme:/oauth2redirect";

  static const ApiConfig disabled = ApiConfig(
    enabled: false,
    baseUrl: "",
    issuer: "",
    clientId: "",
    redirectUri: defaultRedirectUri,
    scopes: "openid",
  );

  final bool enabled;
  final String baseUrl;
  final String issuer;
  final String clientId;
  final String redirectUri;
  final String scopes;

  List<String> get scopeList =>
      scopes.split(RegExp(r"\s+")).where((s) => s.isNotEmpty).toList();

  /// Reasons sign-in cannot be used. Empty when the build is ready (or disabled).
  List<String> get problems {
    if (!enabled) return const [];
    final issues = <String>[];
    if (!_isHttpsUrl(baseUrl)) {
      issues.add("STN_API_BASE_URL must be an https:// address.");
    }
    if (!_isHttpsUrl(issuer)) {
      issues.add("STN_OIDC_ISSUER must be an https:// address.");
    }
    if (clientId.trim().isEmpty) {
      issues.add("STN_OIDC_CLIENT_ID is not set.");
    }
    if (!redirectUri.startsWith("$redirectScheme:")) {
      issues.add("STN_OIDC_REDIRECT_URI must use the $redirectScheme scheme.");
    }
    if (!scopeList.contains("openid")) {
      issues.add("STN_OIDC_SCOPES must include openid.");
    }
    return issues;
  }

  bool get ready => enabled && problems.isEmpty;

  /// Builds an API URL from path segments; each segment is encoded, so ids
  /// cannot change the path.
  Uri endpoint(List<String> segments, [Map<String, String>? query]) {
    final base = Uri.parse(baseUrl);
    final basePath = base.pathSegments.where((s) => s.isNotEmpty);
    return base.replace(
      pathSegments: [...basePath, ...segments],
      queryParameters: query == null || query.isEmpty ? null : query,
    );
  }

  static bool _isHttpsUrl(String value) {
    final uri = Uri.tryParse(value.trim());
    return uri != null && uri.scheme == "https" && uri.host.isNotEmpty;
  }
}

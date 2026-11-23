import "api_config.dart";

/// Tokens from the identity provider. Never logged or shown.
class OidcTokens {
  const OidcTokens({
    required this.accessToken,
    this.refreshToken,
    this.idToken,
    this.expiresAt,
  });

  final String accessToken;
  final String? refreshToken;
  final String? idToken;
  final DateTime? expiresAt;

  bool expiredAt(DateTime now) =>
      expiresAt != null &&
      !now.isBefore(expiresAt!.subtract(const Duration(seconds: 60)));

  Map<String, String> toStorage() => {
        "access_token": accessToken,
        if (refreshToken != null) "refresh_token": refreshToken!,
        if (idToken != null) "id_token": idToken!,
        if (expiresAt != null)
          "expires_at": expiresAt!.toUtc().toIso8601String(),
      };

  static OidcTokens? fromStorage(Map<String, String> values) {
    final access = values["access_token"];
    if (access == null || access.isEmpty) return null;
    return OidcTokens(
      accessToken: access,
      refreshToken: values["refresh_token"],
      idToken: values["id_token"],
      expiresAt: DateTime.tryParse(values["expires_at"] ?? ""),
    );
  }
}

/// System-browser OIDC sign-in (authorisation code + PKCE). The default build
/// has no adapter (see oidc_platform.dart); the clinician API build variant
/// supplies one based on flutter_appauth.
abstract class OidcAdapter {
  Future<OidcTokens> signIn(ApiConfig config);
  Future<OidcTokens> refresh(ApiConfig config, String refreshToken);
  Future<void> signOut(ApiConfig config, String? idTokenHint);
}

class SignInUnavailable implements Exception {
  const SignInUnavailable();

  @override
  String toString() =>
      "Clinician sign-in is not part of this build of the STN app.";
}

class SignInCancelled implements Exception {
  const SignInCancelled();

  @override
  String toString() => "Sign-in was cancelled.";
}

class SignInFailed implements Exception {
  const SignInFailed(this.message);

  final String message;

  @override
  String toString() => message;
}

class UnavailableOidcAdapter implements OidcAdapter {
  const UnavailableOidcAdapter();

  @override
  Future<OidcTokens> signIn(ApiConfig config) =>
      Future.error(const SignInUnavailable());

  @override
  Future<OidcTokens> refresh(ApiConfig config, String refreshToken) =>
      Future.error(const SignInUnavailable());

  @override
  Future<void> signOut(ApiConfig config, String? idTokenHint) async {}
}

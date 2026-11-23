// Clinician API build variant: system-browser OIDC sign-in through
// flutter_appauth (authorisation code flow with PKCE; AppAuth applies PKCE by
// default). Copied over lib/api/oidc_platform.dart by apply_clinician_api.py
// --variant api. The app never sees the user's password; MFA is enforced by
// the identity provider and checked again by the STN API.
import "package:flutter_appauth/flutter_appauth.dart";

import "api_config.dart";
import "oidc.dart";

class AppAuthOidcAdapter implements OidcAdapter {
  const AppAuthOidcAdapter([this._appAuth = const FlutterAppAuth()]);

  final FlutterAppAuth _appAuth;

  @override
  Future<OidcTokens> signIn(ApiConfig config) => _guard(() async {
        final response = await _appAuth.authorizeAndExchangeCode(
          AuthorizationTokenRequest(
            config.clientId,
            config.redirectUri,
            issuer: config.issuer,
            scopes: config.scopeList,
          ),
        );
        return _tokens(response);
      });

  @override
  Future<OidcTokens> refresh(ApiConfig config, String refreshToken) =>
      _guard(() async {
        final response = await _appAuth.token(
          TokenRequest(
            config.clientId,
            config.redirectUri,
            issuer: config.issuer,
            refreshToken: refreshToken,
            scopes: config.scopeList,
          ),
        );
        return _tokens(response, previousRefreshToken: refreshToken);
      });

  @override
  Future<void> signOut(ApiConfig config, String? idTokenHint) async {
    if (idTokenHint == null) return;
    await _guard(() => _appAuth.endSession(
          EndSessionRequest(
            idTokenHint: idTokenHint,
            postLogoutRedirectUrl: config.redirectUri,
            issuer: config.issuer,
          ),
        ));
  }

  static OidcTokens _tokens(TokenResponse response, {String? previousRefreshToken}) {
    final access = response.accessToken;
    if (access == null || access.isEmpty) {
      throw const SignInFailed("The identity provider returned no access token.");
    }
    return OidcTokens(
      accessToken: access,
      refreshToken: response.refreshToken ?? previousRefreshToken,
      idToken: response.idToken,
      expiresAt: response.accessTokenExpirationDateTime,
    );
  }

  static Future<T> _guard<T>(Future<T> Function() action) async {
    try {
      return await action();
    } on FlutterAppAuthUserCancelledException {
      throw const SignInCancelled();
    } on FlutterAppAuthPlatformException catch (error) {
      final details = error.platformErrorDetails;
      throw SignInFailed(
        "Sign-in failed: ${details.errorDescription ?? details.error ?? error.code}.",
      );
    }
  }
}

OidcAdapter createPlatformOidcAdapter() => const AppAuthOidcAdapter();

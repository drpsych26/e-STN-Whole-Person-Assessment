import "api_config.dart";
import "oidc.dart";
import "token_store.dart";

class ApiNotConfigured implements Exception {
  const ApiNotConfigured(this.problems);

  final List<String> problems;

  @override
  String toString() => "Clinician sign-in is not configured in this build.";
}

class NotSignedIn implements Exception {
  const NotSignedIn();

  @override
  String toString() => "Sign in again to continue.";
}

/// Clinician sign-in state. The server decides roles and permissions from the
/// verified token; nothing here grants access.
class AuthService {
  AuthService({
    required this.config,
    required OidcAdapter adapter,
    required TokenStore store,
    DateTime Function()? clock,
  })  : _adapter = adapter,
        _store = store,
        _clock = clock ?? DateTime.now;

  final ApiConfig config;
  final OidcAdapter _adapter;
  final TokenStore _store;
  final DateTime Function() _clock;

  void _requireReady() {
    if (!config.ready) throw ApiNotConfigured(config.problems);
  }

  Future<void> signIn() async {
    _requireReady();
    final tokens = await _adapter.signIn(config);
    await _store.write(tokens);
  }

  Future<bool> get signedIn async => (await _store.read()) != null;

  /// A current access token, refreshed when it is about to expire.
  Future<String> accessToken() async {
    _requireReady();
    final tokens = await _store.read();
    if (tokens == null) throw const NotSignedIn();
    if (!tokens.expiredAt(_clock())) return tokens.accessToken;
    final refreshToken = tokens.refreshToken;
    if (refreshToken == null) {
      await _store.clear();
      throw const NotSignedIn();
    }
    try {
      final renewed = await _adapter.refresh(config, refreshToken);
      await _store.write(renewed);
      return renewed.accessToken;
    } catch (_) {
      await _store.clear();
      throw const NotSignedIn();
    }
  }

  /// Clears local tokens first, then asks the provider to end the session.
  Future<void> signOut() async {
    final tokens = await _store.read();
    await _store.clear();
    if (!config.ready) return;
    try {
      await _adapter.signOut(config, tokens?.idToken);
    } catch (_) {
      // Local tokens are already gone; a failed provider sign-out is not fatal.
    }
  }
}

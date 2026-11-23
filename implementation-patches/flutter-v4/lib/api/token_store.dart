import "package:flutter_secure_storage/flutter_secure_storage.dart";

import "oidc.dart";

/// Where sign-in tokens live. Production uses the platform keystore through
/// flutter_secure_storage; nothing else in the app may hold them.
abstract class TokenStore {
  Future<OidcTokens?> read();
  Future<void> write(OidcTokens tokens);
  Future<void> clear();
}

class SecureTokenStore implements TokenStore {
  SecureTokenStore([FlutterSecureStorage? storage])
      : _storage = storage ?? const FlutterSecureStorage();

  static const _prefix = "stn.clinician.";
  static const _keys = ["access_token", "refresh_token", "id_token", "expires_at"];
  final FlutterSecureStorage _storage;

  @override
  Future<OidcTokens?> read() async {
    final values = <String, String>{};
    for (final key in _keys) {
      final value = await _storage.read(key: "$_prefix$key");
      if (value != null) values[key] = value;
    }
    return OidcTokens.fromStorage(values);
  }

  @override
  Future<void> write(OidcTokens tokens) async {
    await clear();
    for (final entry in tokens.toStorage().entries) {
      await _storage.write(key: "$_prefix${entry.key}", value: entry.value);
    }
  }

  @override
  Future<void> clear() async {
    for (final key in _keys) {
      await _storage.delete(key: "$_prefix$key");
    }
  }
}

/// In-memory store for tests only.
class MemoryTokenStore implements TokenStore {
  OidcTokens? _tokens;

  @override
  Future<OidcTokens?> read() async => _tokens;

  @override
  Future<void> write(OidcTokens tokens) async => _tokens = tokens;

  @override
  Future<void> clear() async => _tokens = null;
}

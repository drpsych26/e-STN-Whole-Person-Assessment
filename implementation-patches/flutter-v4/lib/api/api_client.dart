import "dart:convert";

import "api_config.dart";
import "transport.dart";

/// An API error, with the server's detail message when it sent one.
class ApiException implements Exception {
  const ApiException(this.statusCode, this.message);

  final int statusCode;
  final String message;

  bool get unauthorised => statusCode == 401;
  bool get forbidden => statusCode == 403;
  bool get notFound => statusCode == 404;
  bool get conflict => statusCode == 409;
  bool get gone => statusCode == 410;
  bool get rateLimited => statusCode == 429;

  @override
  String toString() => message;
}

typedef AccessTokenProvider = Future<String> Function();

/// Client for the STN API clinician review workflow (backend PR #54).
///
/// Every call carries the bearer token; roles, organisation and visibility are
/// decided by the server. Responses are generic JSON maps: this client adds no
/// clinical logic.
class ApiClient {
  ApiClient({
    required this.config,
    required ApiTransport transport,
    required AccessTokenProvider accessToken,
  })  : _transport = transport,
        _accessToken = accessToken;

  final ApiConfig config;
  final ApiTransport _transport;
  final AccessTokenProvider _accessToken;

  Future<Map<String, dynamic>> access() async =>
      _object(await _call("GET", ["v1", "me", "access"]));

  Future<List<Map<String, dynamic>>> reviewQueue() async =>
      _list(await _call("GET", ["v1", "review-queue"]));

  Future<Map<String, dynamic>> assessment(String id) async =>
      _object(await _call("GET", ["v1", "assessments", id]));

  Future<List<Map<String, dynamic>>> safetyFlags(String id) async =>
      _list(await _call("GET", ["v1", "assessments", id, "safety-flags"]));

  Future<Map<String, dynamic>> acknowledgeFlag(String id, String flagId) async =>
      _object(await _call(
        "POST",
        ["v1", "assessments", id, "safety-flags", flagId, "acknowledge"],
      ));

  Future<Map<String, dynamic>> submit(String id, List<String> safetyFlags) async =>
      _object(await _call(
        "POST",
        ["v1", "assessments", id, "submit"],
        {"safety_flags": safetyFlags},
      ));

  Future<Map<String, dynamic>> startReview(String id) async =>
      _object(await _call("POST", ["v1", "assessments", id, "start-review"]));

  Future<Map<String, dynamic>> returnForChanges(String id, String reason) async =>
      _object(await _call(
        "POST",
        ["v1", "assessments", id, "return"],
        {"reason": reason},
      ));

  Future<Map<String, dynamic>> signOff(String id, String contentHash) async =>
      _object(await _call(
        "POST",
        ["v1", "assessments", id, "sign-off"],
        {"content_hash": contentHash},
      ));

  Future<Object?> _call(
    String method,
    List<String> path, [
    Map<String, Object?>? body,
  ]) async {
    if (!config.ready) {
      throw const ApiException(0, "Clinician sign-in is not configured in this build.");
    }
    final token = await _accessToken();
    final hasBody = method != "GET";
    final response = await _transport.send(
      method,
      config.endpoint(path),
      headers: {
        "Authorization": "Bearer $token",
        "Accept": "application/json",
        if (hasBody) "Content-Type": "application/json",
      },
      body: hasBody ? jsonEncode(body ?? const <String, Object?>{}) : null,
    );
    final decoded = _decode(response.body);
    if (response.statusCode >= 200 && response.statusCode < 300) return decoded;
    throw ApiException(response.statusCode, _message(response, decoded));
  }

  static Object? _decode(String body) {
    if (body.isEmpty) return null;
    try {
      return jsonDecode(body);
    } on FormatException {
      return null;
    }
  }

  static String _message(ApiResponse response, Object? decoded) {
    final detail = decoded is Map ? decoded["detail"] : null;
    if (detail is String && detail.isNotEmpty) return detail;
    switch (response.statusCode) {
      case 401:
        return "Sign in again to continue.";
      case 403:
        return "Your account is not permitted to do this.";
      case 404:
        return "Record not found.";
      case 409:
        return "The record changed; reload and try again.";
      case 410:
        return "This record was disposed under the retention policy.";
      case 429:
        final retry = response.headers["retry-after"];
        return retry == null
            ? "Too many requests; try again shortly."
            : "Too many requests; try again in $retry seconds.";
      default:
        return "The STN service could not complete the request (${response.statusCode}).";
    }
  }

  static Map<String, dynamic> _object(Object? value) {
    if (value is Map<String, dynamic>) return value;
    throw const ApiException(0, "Unexpected response from the STN service.");
  }

  static List<Map<String, dynamic>> _list(Object? value) {
    if (value is List) {
      return [for (final item in value) _object(item)];
    }
    throw const ApiException(0, "Unexpected response from the STN service.");
  }
}

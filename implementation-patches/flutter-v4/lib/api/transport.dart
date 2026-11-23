/// HTTP transport used by [ApiClient]. The default build has no transport
/// (see transport_platform.dart); the clinician API build variant supplies
/// one based on package:http.
abstract class ApiTransport {
  Future<ApiResponse> send(
    String method,
    Uri url, {
    Map<String, String> headers = const {},
    String? body,
  });
}

class ApiResponse {
  const ApiResponse(this.statusCode, this.body, [this.headers = const {}]);

  final int statusCode;
  final String body;
  final Map<String, String> headers;
}

/// Raised when the build has no network transport (the offline default).
class TransportUnavailable implements Exception {
  const TransportUnavailable();

  @override
  String toString() =>
      "Network access is not part of this build of the STN app.";
}

class UnavailableTransport implements ApiTransport {
  const UnavailableTransport();

  @override
  Future<ApiResponse> send(
    String method,
    Uri url, {
    Map<String, String> headers = const {},
    String? body,
  }) =>
      Future.error(const TransportUnavailable());
}

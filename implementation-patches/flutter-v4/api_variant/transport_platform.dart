// Clinician API build variant: HTTPS transport through package:http.
// Copied over lib/api/transport_platform.dart by apply_clinician_api.py
// --variant api. Redirects are not followed, so the bearer token is never
// forwarded to another host; plain http:// is refused.
import "package:http/http.dart" as http;

import "transport.dart";

class HttpApiTransport implements ApiTransport {
  HttpApiTransport({http.Client? client, this.timeout = const Duration(seconds: 30)})
      : _client = client ?? http.Client();

  final http.Client _client;
  final Duration timeout;

  @override
  Future<ApiResponse> send(
    String method,
    Uri url, {
    Map<String, String> headers = const {},
    String? body,
  }) async {
    if (url.scheme != "https") {
      throw ArgumentError.value(url.scheme, "url", "Only https:// is allowed");
    }
    final request = http.Request(method, url)
      ..followRedirects = false
      ..headers.addAll(headers);
    if (body != null) request.body = body;
    final streamed = await _client.send(request).timeout(timeout);
    final response = await http.Response.fromStream(streamed).timeout(timeout);
    return ApiResponse(response.statusCode, response.body, response.headers);
  }
}

ApiTransport createPlatformTransport() => HttpApiTransport();

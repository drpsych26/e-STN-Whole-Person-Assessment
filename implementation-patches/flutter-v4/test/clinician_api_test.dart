import "dart:convert";

import "package:flutter_test/flutter_test.dart";
import "package:supportive_therapy_network/api/api_client.dart";
import "package:supportive_therapy_network/api/api_config.dart";
import "package:supportive_therapy_network/api/auth_service.dart";
import "package:supportive_therapy_network/api/oidc.dart";
import "package:supportive_therapy_network/api/token_store.dart";
import "package:supportive_therapy_network/api/transport.dart";

const ready = ApiConfig(
  enabled: true,
  baseUrl: "https://api.synthetic.invalid/stn",
  issuer: "https://login.synthetic.invalid/tenant/v2.0",
  clientId: "00000000-0000-0000-0000-000000000000",
  redirectUri: ApiConfig.defaultRedirectUri,
  scopes: "openid profile offline_access",
);

class RecordedRequest {
  RecordedRequest(this.method, this.url, this.headers, this.body);
  final String method;
  final Uri url;
  final Map<String, String> headers;
  final String? body;
}

class FakeTransport implements ApiTransport {
  FakeTransport(this.respond);

  final ApiResponse Function(RecordedRequest request) respond;
  final requests = <RecordedRequest>[];

  @override
  Future<ApiResponse> send(
    String method,
    Uri url, {
    Map<String, String> headers = const {},
    String? body,
  }) async {
    final request = RecordedRequest(method, url, headers, body);
    requests.add(request);
    return respond(request);
  }
}

class FakeOidc implements OidcAdapter {
  FakeOidc({this.expiresAt, this.failRefresh = false, this.failSignOut = false});

  final DateTime? expiresAt;
  final bool failRefresh;
  final bool failSignOut;
  int signIns = 0, refreshes = 0, signOuts = 0;

  @override
  Future<OidcTokens> signIn(ApiConfig config) async {
    signIns++;
    return OidcTokens(
      accessToken: "synthetic-access-1",
      refreshToken: "synthetic-refresh",
      idToken: "synthetic-id",
      expiresAt: expiresAt,
    );
  }

  @override
  Future<OidcTokens> refresh(ApiConfig config, String refreshToken) async {
    refreshes++;
    if (failRefresh) throw const SignInFailed("refresh refused");
    return OidcTokens(
      accessToken: "synthetic-access-2",
      refreshToken: refreshToken,
      expiresAt: DateTime.utc(2100),
    );
  }

  @override
  Future<void> signOut(ApiConfig config, String? idTokenHint) async {
    signOuts++;
    if (failSignOut) throw const SignInFailed("provider unavailable");
  }
}

ApiClient clientWith(FakeTransport transport, [ApiConfig config = ready]) =>
    ApiClient(config: config, transport: transport, accessToken: () async => "synthetic-token");

void main() {
  group("ApiConfig", () {
    test("disabled by default and reports no problems", () {
      expect(ApiConfig.disabled.ready, isFalse);
      expect(ApiConfig.disabled.problems, isEmpty);
      expect(const ApiConfig.fromEnvironment().enabled, isFalse);
    });

    test("enabled but unconfigured fails closed with reasons", () {
      const config = ApiConfig(
        enabled: true,
        baseUrl: "http://api.synthetic.invalid",
        issuer: "",
        clientId: " ",
        redirectUri: "https://wrong.invalid/cb",
        scopes: "profile",
      );
      expect(config.ready, isFalse);
      expect(config.problems, hasLength(5));
      expect(config.problems.first, contains("https://"));
    });

    test("ready configuration builds encoded endpoints under the base path", () {
      expect(ready.ready, isTrue);
      final url = ready.endpoint(["v1", "assessments", "a/../b?x=1"]);
      expect(url.scheme, "https");
      expect(url.path, "/stn/v1/assessments/a%2F..%2Fb%3Fx=1");
      expect(url.query, isEmpty);
    });
  });

  group("ApiClient", () {
    test("sends bearer token and JSON to the review endpoints", () async {
      final transport = FakeTransport((r) => const ApiResponse(200, '{"state":"submitted"}'));
      final client = clientWith(transport);
      await client.submit("a-1", ["synthetic_flag"]);
      final request = transport.requests.single;
      expect(request.method, "POST");
      expect(request.url.toString(), "https://api.synthetic.invalid/stn/v1/assessments/a-1/submit");
      expect(request.headers["Authorization"], "Bearer synthetic-token");
      expect(request.headers["Content-Type"], "application/json");
      expect(jsonDecode(request.body!), {"safety_flags": ["synthetic_flag"]});

      await client.signOff("a-1", "f" * 64);
      expect(jsonDecode(transport.requests.last.body!), {"content_hash": "f" * 64});
      await client.returnForChanges("a-1", "Synthetic reason.");
      expect(transport.requests.last.url.path, "/stn/v1/assessments/a-1/return");
    });

    test("GET requests carry no body", () async {
      final transport = FakeTransport((r) => const ApiResponse(200, "[]"));
      expect(await clientWith(transport).reviewQueue(), isEmpty);
      expect(transport.requests.single.method, "GET");
      expect(transport.requests.single.body, isNull);
      expect(transport.requests.single.headers.containsKey("Content-Type"), isFalse);
    });

    test("maps server errors to messages without leaking tokens", () async {
      final responses = [
        const ApiResponse(409, '{"detail":"Every safety flag must be acknowledged first."}'),
        const ApiResponse(429, "", {"retry-after": "30"}),
        const ApiResponse(410, ""),
        const ApiResponse(403, '{"detail":"Multi-factor authentication is required."}'),
      ];
      var i = 0;
      final client = clientWith(FakeTransport((r) => responses[i++]));
      Future<ApiException> failure(Future<Object?> call) async {
        try {
          await call;
        } on ApiException catch (e) {
          return e;
        }
        fail("expected an ApiException");
      }

      final conflict = await failure(client.startReview("a-1"));
      expect(conflict.conflict, isTrue);
      expect(conflict.message, contains("acknowledged"));
      final limited = await failure(client.startReview("a-1"));
      expect(limited.rateLimited, isTrue);
      expect(limited.message, contains("30 seconds"));
      expect((await failure(client.assessment("a-1"))).gone, isTrue);
      final forbidden = await failure(client.reviewQueue());
      expect(forbidden.forbidden, isTrue);
      expect(forbidden.toString(), isNot(contains("synthetic-token")));
    });

    test("refuses to call when the build is not configured", () async {
      final transport = FakeTransport((r) => const ApiResponse(200, "{}"));
      await expectLater(clientWith(transport, ApiConfig.disabled).access(), throwsA(isA<ApiException>()));
      expect(transport.requests, isEmpty);
    });
  });

  group("AuthService", () {
    test("signs in, stores tokens and signs out clearing them", () async {
      final oidc = FakeOidc(failSignOut: true);
      final store = MemoryTokenStore();
      final auth = AuthService(config: ready, adapter: oidc, store: store);
      await auth.signIn();
      expect(await auth.signedIn, isTrue);
      expect(await auth.accessToken(), "synthetic-access-1");
      await auth.signOut();
      expect(await store.read(), isNull);
      expect(oidc.signOuts, 1);
      await expectLater(auth.accessToken(), throwsA(isA<NotSignedIn>()));
    });

    test("refreshes an expiring token and fails closed when refresh fails", () async {
      final now = DateTime.utc(2026, 11, 23, 12);
      final store = MemoryTokenStore();
      final oidc = FakeOidc(expiresAt: now.add(const Duration(seconds: 30)));
      final auth = AuthService(config: ready, adapter: oidc, store: store, clock: () => now);
      await auth.signIn();
      expect(await auth.accessToken(), "synthetic-access-2");
      expect(oidc.refreshes, 1);

      final failing = FakeOidc(expiresAt: now, failRefresh: true);
      final auth2 = AuthService(config: ready, adapter: failing, store: store, clock: () => now);
      await auth2.signIn();
      await expectLater(auth2.accessToken(), throwsA(isA<NotSignedIn>()));
      expect(await store.read(), isNull);
    });

    test("does not start sign-in when the build is not configured", () async {
      final oidc = FakeOidc();
      final auth = AuthService(config: ApiConfig.disabled, adapter: oidc, store: MemoryTokenStore());
      await expectLater(auth.signIn(), throwsA(isA<ApiNotConfigured>()));
      expect(oidc.signIns, 0);
    });
  });

  group("offline stubs used by the default build", () {
    test("have no network and no sign-in", () async {
      await expectLater(
        const UnavailableTransport().send("GET", Uri.parse("https://api.synthetic.invalid")),
        throwsA(isA<TransportUnavailable>()),
      );
      await expectLater(const UnavailableOidcAdapter().signIn(ready), throwsA(isA<SignInUnavailable>()));
    });
  });
}

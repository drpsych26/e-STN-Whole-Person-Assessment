import "dart:convert";

import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:supportive_therapy_network/api/api_client.dart";
import "package:supportive_therapy_network/api/api_config.dart";
import "package:supportive_therapy_network/api/auth_service.dart";
import "package:supportive_therapy_network/api/oidc.dart";
import "package:supportive_therapy_network/api/token_store.dart";
import "package:supportive_therapy_network/api/transport.dart";
import "package:supportive_therapy_network/screens/clinician/clinician_services.dart";
import "package:supportive_therapy_network/screens/home_screen.dart";

const ready = ApiConfig(
  enabled: true,
  baseUrl: "https://api.synthetic.invalid",
  issuer: "https://login.synthetic.invalid/tenant/v2.0",
  clientId: "00000000-0000-0000-0000-000000000000",
  redirectUri: ApiConfig.defaultRedirectUri,
  scopes: "openid profile offline_access",
);

const _hash = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa";

class _Oidc implements OidcAdapter {
  @override
  Future<OidcTokens> signIn(ApiConfig config) async =>
      const OidcTokens(accessToken: "synthetic-access");

  @override
  Future<OidcTokens> refresh(ApiConfig config, String refreshToken) async =>
      const OidcTokens(accessToken: "synthetic-access");

  @override
  Future<void> signOut(ApiConfig config, String? idTokenHint) async {}
}

/// A tiny synthetic STN API: one submitted assessment with one safety flag.
class _FakeApi implements ApiTransport {
  String state = "submitted";
  bool acknowledged = false;
  final calls = <String>[];

  Map<String, dynamic> get _flag => {
        "id": "flag-1",
        "code": "synthetic_flag",
        "raised_by": "clin-1",
        "raised_at": "2026-11-23T00:00:00+00:00",
        "acknowledged_by": acknowledged ? "rev-1" : null,
        "acknowledged_at": acknowledged ? "2026-11-23T00:01:00+00:00" : null,
      };

  Map<String, dynamic> get _meta => {
        "id": "a-1",
        "form_id": "whole_person_initial",
        "form_version": "v2.6",
        "state": state,
        "version": 1,
        "content_hash": _hash,
        "submitted_at": "2026-11-23T00:00:00+00:00",
        "reviewer_sub": state == "submitted" ? null : "rev-1",
        "signed_off_by": state == "signed_off" ? "rev-1" : null,
        "signed_off_at": state == "signed_off" ? "2026-11-23T00:05:00+00:00" : null,
      };

  @override
  Future<ApiResponse> send(String method, Uri url, {Map<String, String> headers = const {}, String? body}) async {
    expect(headers["Authorization"], "Bearer synthetic-access");
    final path = url.path;
    calls.add("$method $path");
    ApiResponse ok(Object value) => ApiResponse(200, jsonEncode(value));
    switch ("$method $path") {
      case "GET /v1/me/access":
        return ok({"subject": "rev-1", "roles": ["reviewer"], "organisation": "org-synthetic-1", "mfa": true});
      case "GET /v1/review-queue":
        return ok([
          if (state == "submitted" || state == "in_review")
            {..._meta, "unacknowledged_safety_flags": acknowledged ? 0 : 1},
        ]);
      case "GET /v1/assessments/a-1":
        if (state == "submitted") {
          return const ApiResponse(404, '{"detail":"Record not found."}');
        }
        return ok({..._meta, "payload": {"synthetic_item_1": "synthetic answer"}, "note": null, "safety_flags": [_flag]});
      case "GET /v1/assessments/a-1/safety-flags":
        return ok([_flag]);
      case "POST /v1/assessments/a-1/safety-flags/flag-1/acknowledge":
        acknowledged = true;
        return ok(_flag);
      case "POST /v1/assessments/a-1/start-review":
        if (!acknowledged) {
          return const ApiResponse(409, '{"detail":"Acknowledge every flag first."}');
        }
        state = "in_review";
        return ok(_meta);
      case "POST /v1/assessments/a-1/sign-off":
        expect(jsonDecode(body!), {"content_hash": _hash});
        state = "signed_off";
        return ok(_meta);
    }
    return const ApiResponse(404, '{"detail":"Record not found."}');
  }
}

ClinicianServices _services(ApiConfig config, _FakeApi api) {
  final auth = AuthService(config: config, adapter: _Oidc(), store: MemoryTokenStore());
  return ClinicianServices(
    auth: auth,
    client: ApiClient(config: config, transport: api, accessToken: auth.accessToken),
  );
}

Future<void> _pumpHome(WidgetTester tester, Widget home) async {
  tester.view.physicalSize = const Size(900, 2200);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(() {
    tester.view.resetPhysicalSize();
    tester.view.resetDevicePixelRatio();
  });
  await tester.pumpWidget(MaterialApp(home: home));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets("sign-in entry is absent when the flag is off", (tester) async {
    await _pumpHome(tester, const HomeScreen());
    expect(find.byKey(const ValueKey("clinician-sign-in-entry")), findsNothing);
    expect(find.text("Clinician sign-in"), findsNothing);
    await _pumpHome(tester, const HomeScreen(apiConfig: ApiConfig.disabled));
    expect(find.byKey(const ValueKey("clinician-sign-in-entry")), findsNothing);
  });

  testWidgets("enabled but unconfigured build explains why and offers no sign-in", (tester) async {
    const broken = ApiConfig(
      enabled: true,
      baseUrl: "",
      issuer: "",
      clientId: "",
      redirectUri: ApiConfig.defaultRedirectUri,
      scopes: "openid",
    );
    await _pumpHome(tester, HomeScreen(apiConfig: broken, clinicianServices: (c) => _services(c, _FakeApi())));
    expect(find.text("Not configured in this build"), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey("clinician-sign-in-entry")));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey("clinician-sign-in-not-configured")), findsOneWidget);
    expect(find.byKey(const ValueKey("clinician-sign-in-button")), findsNothing);
  });

  testWidgets("signed-in reviewer acknowledges the flag, starts review and signs off", (tester) async {
    final api = _FakeApi();
    await _pumpHome(tester, HomeScreen(apiConfig: ready, clinicianServices: (c) => _services(c, api)));

    expect(find.byKey(const ValueKey("clinician-sign-in-entry")), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey("clinician-sign-in-entry")));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey("clinician-sign-in-button")));
    await tester.pumpAndSettle();
    expect(find.text("Signed in as rev-1"), findsOneWidget);
    expect(find.textContaining("Organisation: org-synthetic-1"), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey("clinician-review-queue-entry")));
    await tester.pumpAndSettle();
    expect(find.text("1 flag to acknowledge"), findsOneWidget);
    await tester.tap(find.byKey(const ValueKey("queue-item-a-1")));
    await tester.pumpAndSettle();

    expect(find.text("State: submitted"), findsOneWidget);
    final start = find.byKey(const ValueKey("action-start-review"));
    expect(tester.widget<FilledButton>(start).onPressed, isNull);

    await tester.tap(find.byKey(const ValueKey("acknowledge-flag-1")));
    await tester.pumpAndSettle();
    expect(find.textContaining("not a risk assessment"), findsOneWidget);
    await tester.tap(find.widgetWithText(FilledButton, "Acknowledge"));
    await tester.pumpAndSettle();
    expect(api.acknowledged, isTrue);
    expect(find.textContaining("Acknowledged by rev-1"), findsOneWidget);

    expect(tester.widget<FilledButton>(start).onPressed, isNotNull);
    await tester.tap(start);
    await tester.pumpAndSettle();
    expect(find.text("State: in_review"), findsOneWidget);
    expect(find.textContaining("synthetic answer"), findsOneWidget);

    await tester.tap(find.byKey(const ValueKey("action-sign-off")));
    await tester.pumpAndSettle();
    expect(find.textContaining(_hash), findsWidgets);
    await tester.tap(find.widgetWithText(FilledButton, "Sign off").last);
    await tester.pumpAndSettle();
    expect(find.text("State: signed_off"), findsOneWidget);
    expect(api.calls, contains("POST /v1/assessments/a-1/sign-off"));
  });
}

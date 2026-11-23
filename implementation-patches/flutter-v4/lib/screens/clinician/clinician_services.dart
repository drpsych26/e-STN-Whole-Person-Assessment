import "../../api/api_client.dart";
import "../../api/api_config.dart";
import "../../api/auth_service.dart";
import "../../api/oidc_platform.dart";
import "../../api/token_store.dart";
import "../../api/transport_platform.dart";

/// Sign-in and API client for the clinician screens.
class ClinicianServices {
  ClinicianServices({required this.auth, required this.client});

  /// Platform implementations: in the default build these are the offline
  /// stubs; the clinician API build variant swaps in AppAuth and package:http.
  factory ClinicianServices.platform(ApiConfig config) {
    final auth = AuthService(
      config: config,
      adapter: createPlatformOidcAdapter(),
      store: SecureTokenStore(),
    );
    return ClinicianServices(
      auth: auth,
      client: ApiClient(
        config: config,
        transport: createPlatformTransport(),
        accessToken: auth.accessToken,
      ),
    );
  }

  final AuthService auth;
  final ApiClient client;

  ApiConfig get config => auth.config;
}

const String syntheticDataNotice =
    "Synthetic data only. Do not enter identifiable client information until "
    "every STN go-live gate has been signed off.";

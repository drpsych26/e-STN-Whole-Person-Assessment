import "dart:convert";
import "dart:math";
import "package:flutter_secure_storage/flutter_secure_storage.dart";
import "package:hive/hive.dart";
import "../models/assessment_models.dart";
import "../models/profile_models.dart";

class SecureHive {
  static const _secureKeyName = "stn_hive_key_v1";
  static const String resultsBoxName = "stn_results_box";
  static const String profilesBoxName = "stn_profiles_box";

  static const FlutterSecureStorage _secureStorage = FlutterSecureStorage();

  static Future<void> initEncryptedBoxes() async {
    final key = await _getOrCreateKey();
    if (!Hive.isBoxOpen(resultsBoxName)) {
      await Hive.openBox(resultsBoxName, encryptionCipher: HiveAesCipher(key));
    }
    if (!Hive.isBoxOpen(profilesBoxName)) {
      await Hive.openBox(profilesBoxName, encryptionCipher: HiveAesCipher(key));
    }
  }

  static Future<List<int>> _getOrCreateKey() async {
    final existing = await _secureStorage.read(key: _secureKeyName);
    if (existing != null) {
      final key = base64Url.decode(existing);
      if (key.length != 32) {
        throw StateError('Stored STN encryption key has an invalid length.');
      }
      return key;
    }

    final random = Random.secure();
    final key = List<int>.generate(32, (_) => random.nextInt(256));
    await _secureStorage.write(
      key: _secureKeyName,
      value: base64Url.encode(key),
    );
    return key;
  }

  static Box get _results => Hive.box(resultsBoxName);
  static Box get _profiles => Hive.box(profilesBoxName);

  static Future<void> addResult(ModuleResult result) async {
    await _results.add(result.toJson());
  }

  static List<ModuleResult> loadResults() {
    final results = _results.values.map((value) {
      if (value is! Map) {
        throw const FormatException('Stored assessment result is not a map.');
      }
      return ModuleResult.fromJson(Map<String, dynamic>.from(value));
    }).toList();
    results.sort((a, b) => b.completedAt.compareTo(a.completedAt));
    return results;
  }

  static Future<void> clearResults() async {
    await _results.clear();
  }

  static Future<void> saveActiveClient(ClientProfile client) async {
    await _profiles.put("active_client", client.toJson());
  }

  static ClientProfile? loadActiveClient() {
    final raw = _profiles.get("active_client");
    if (raw == null) return null;
    if (raw is! Map) {
      throw const FormatException('Stored client profile is invalid.');
    }
    return ClientProfile.fromJson(Map<String, dynamic>.from(raw));
  }

  static Future<void> saveActiveClinician(ClinicianProfile clinician) async {
    await _profiles.put("active_clinician", clinician.toJson());
  }

  static ClinicianProfile? loadActiveClinician() {
    final raw = _profiles.get("active_clinician");
    if (raw == null) return null;
    if (raw is! Map) {
      throw const FormatException('Stored clinician profile is invalid.');
    }
    return ClinicianProfile.fromJson(Map<String, dynamic>.from(raw));
  }

  static Future<void> clearProfiles() async {
    await _profiles.clear();
  }
}

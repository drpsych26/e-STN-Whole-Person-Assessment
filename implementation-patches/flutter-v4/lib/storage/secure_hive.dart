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
  static const String wholePersonDraftsBoxName = "stn_whole_person_drafts_box";

  static const FlutterSecureStorage _secureStorage = FlutterSecureStorage();

  static Future<void> initEncryptedBoxes() async {
    final key = await _getOrCreateKey();
    if (!Hive.isBoxOpen(resultsBoxName)) {
      await Hive.openBox(resultsBoxName, encryptionCipher: HiveAesCipher(key));
    }
    if (!Hive.isBoxOpen(profilesBoxName)) {
      await Hive.openBox(profilesBoxName, encryptionCipher: HiveAesCipher(key));
    }
    if (!Hive.isBoxOpen(wholePersonDraftsBoxName)) {
      await Hive.openBox<String>(wholePersonDraftsBoxName, encryptionCipher: HiveAesCipher(key));
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
  static Box<String> get _wholePersonDrafts => Hive.box<String>(wholePersonDraftsBoxName);

  static Future<void> addResult(ModuleResult result) async {
    final client = loadActiveClient();
    final clinician = loadActiveClinician();
    if (client == null || !client.id.startsWith('SYNTH-')) {
      throw StateError('A synthetic case must be active before saving a response summary.');
    }
    if (clinician == null || !clinician.name.startsWith('TESTER-')) {
      throw StateError('A synthetic tester alias must be active before saving a response summary.');
    }
    final payload = Map<String, dynamic>.from(result.toJson())
      ..['_stnSyntheticCaseId'] = client.id
      ..['_stnTesterAlias'] = clinician.name;
    await _results.add(payload);
  }

  static List<ModuleResult> loadResults() {
    final client = loadActiveClient();
    if (client == null || !client.id.startsWith('SYNTH-')) {
      return <ModuleResult>[];
    }
    final results = _results.values
        .where((value) =>
            value is Map && value['_stnSyntheticCaseId'] == client.id)
        .map((value) => ModuleResult.fromJson(Map<String, dynamic>.from(value)))
        .toList();
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

  static Future<void> saveWholePersonDraft(Map<String, dynamic> draft) async {
    final id = draft["id"];
    if (id is! String || id.isEmpty) {
      throw ArgumentError("Whole-person draft requires a non-empty ID.");
    }
    await _wholePersonDrafts.put(id, jsonEncode(draft));
  }

  static Map<String, dynamic>? loadWholePersonDraft(String id) {
    final raw = _wholePersonDrafts.get(id);
    if (raw == null) return null;
    final decoded = jsonDecode(raw);
    if (decoded is! Map) {
      throw const FormatException("Stored whole-person draft is invalid.");
    }
    return Map<String, dynamic>.from(decoded);
  }

  static List<Map<String, dynamic>> loadWholePersonDrafts() {
    final drafts = _wholePersonDrafts.values.map((raw) {
      final decoded = jsonDecode(raw);
      if (decoded is! Map) {
        throw const FormatException("Stored whole-person draft is invalid.");
      }
      return Map<String, dynamic>.from(decoded);
    }).toList();
    drafts.sort((a, b) => (b["updatedAt"] as String? ?? "")
        .compareTo(a["updatedAt"] as String? ?? ""));
    return drafts;
  }

  static Future<void> deleteWholePersonDraft(String id) async {
    await _wholePersonDrafts.delete(id);
  }
}

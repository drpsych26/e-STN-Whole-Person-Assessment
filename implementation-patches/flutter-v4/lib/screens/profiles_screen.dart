import "package:flutter/material.dart";
import "package:uuid/uuid.dart";
import "../models/profile_models.dart";
import "../storage/secure_hive.dart";
import "whole_person_initial_assessment_screen.dart";

class ProfilesScreen extends StatefulWidget {
  const ProfilesScreen({super.key});

  @override
  State<ProfilesScreen> createState() => _ProfilesScreenState();
}

class _ProfilesScreenState extends State<ProfilesScreen> {
  final _uuid = const Uuid();
  final _caseId = TextEditingController();
  final _testerAlias = TextEditingController();
  bool _saving = false;
  bool _legacyProfileDetected = false;
  String? _loadError;

  @override
  void initState() {
    super.initState();
    try {
      final client = SecureHive.loadActiveClient();
      final clinician = SecureHive.loadActiveClinician();
      if (client != null && CoreIntakeRules.isSyntheticCaseId(client.id)) {
        _caseId.text = client.id;
      } else if (client != null) {
        _legacyProfileDetected = true;
        _loadError = "A legacy profile exists but is hidden because it is not a SYNTH- test ID. Clear it before UAT.";
      }
      if (clinician != null && CoreIntakeRules.isSyntheticTesterAlias(clinician.name)) {
        _testerAlias.text = clinician.name;
      } else if (clinician != null) {
        _legacyProfileDetected = true;
        _loadError = "A legacy non-synthetic tester profile is hidden. Clear it before UAT.";
      }
    } catch (error) {
      _loadError = error.toString();
    }
  }

  @override
  void dispose() {
    _caseId.dispose();
    _testerAlias.dispose();
    super.dispose();
  }

  void _message(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message)),
    );
  }

  Future<void> _save() async {
    if (_saving) return;
    final caseId = _caseId.text.trim();
    final testerAlias = _testerAlias.text.trim();
    if (_legacyProfileDetected) {
      _message("Clear legacy non-synthetic profile data before starting UAT.");
      return;
    }
    if (!CoreIntakeRules.isSyntheticCaseId(caseId)) {
      _message("Client profile must use a synthetic ID beginning with SYNTH-. Real client identifiers are blocked.");
      return;
    }
    if (!CoreIntakeRules.isSyntheticTesterAlias(testerAlias)) {
      _message("Use a test alias beginning with TESTER-. Real names are not accepted.");
      return;
    }

    setState(() => _saving = true);
    try {
      final existingClinician = SecureHive.loadActiveClinician();
      final client = ClientProfile(
        id: caseId,
        fullName: "Synthetic case $caseId",
        dobIso: "",
        contact: "",
      );
      final clinician = ClinicianProfile(
        id: existingClinician?.id ?? _uuid.v4(),
        name: testerAlias,
        title: "UAT tester",
        registration: "NOT-APPLICABLE",
      );
      await SecureHive.saveActiveClient(client);
      await SecureHive.saveActiveClinician(clinician);
      _message("Synthetic test profiles saved to encrypted device-local demo storage.");
    } catch (error) {
      _message("Could not save synthetic profiles: $error");
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _clear() async {
    if (_saving) return;
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text("Clear local test profiles?"),
        content: const Text("This removes both current and legacy device-local profile data from this app."),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, false),
            child: const Text("Cancel"),
          ),
          TextButton(
            onPressed: () => Navigator.pop(dialogContext, true),
            child: const Text("Clear"),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    setState(() => _saving = true);
    try {
      await SecureHive.clearProfiles();
      if (!mounted) return;
      _caseId.clear();
      _testerAlias.clear();
      setState(() {
        _loadError = null;
        _legacyProfileDetected = false;
      });
      _message("All device-local test profile data cleared.");
    } catch (error) {
      _message("Could not clear profiles: $error");
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Synthetic Test Profiles"),
        actions: [
          IconButton(
            icon: const Icon(Icons.delete_outline),
            tooltip: "Clear all local profile data",
            onPressed: _saving ? null : _clear,
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Card(
            child: Padding(
              padding: EdgeInsets.all(14),
              child: Text(
                "PRIVATE UAT ONLY — SYNTHETIC DATA ONLY. "
                "This profile screen does not collect client names, dates of birth, contact details or NHI numbers. "
                "These local test profiles are not authenticated identities or clinical records.",
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
          ),
          if (_loadError != null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: Text(
                _loadError!,
                style: const TextStyle(color: Colors.red),
              ),
            ),
          const SizedBox(height: 12),
          const Text("Synthetic case", style: TextStyle(fontWeight: FontWeight.w700)),
          TextField(
            controller: _caseId,
            decoration: const InputDecoration(
              labelText: "Synthetic case ID",
              hintText: "SYNTH-TEST-001",
              helperText: "Must begin with SYNTH-. Real client identifiers are rejected.",
            ),
            textCapitalization: TextCapitalization.characters,
          ),
          const SizedBox(height: 20),
          const Text("UAT tester", style: TextStyle(fontWeight: FontWeight.w700)),
          TextField(
            controller: _testerAlias,
            decoration: const InputDecoration(
              labelText: "Synthetic tester alias",
              hintText: "TESTER-01",
              helperText: "Must begin with TESTER-. Do not enter a real person's name.",
            ),
            textCapitalization: TextCapitalization.characters,
          ),
          const SizedBox(height: 20),
          ElevatedButton(
            onPressed: _saving ? null : _save,
            child: Text(_saving ? "Saving…" : "Save Synthetic Profiles"),
          ),
        ],
      ),
    );
  }
}

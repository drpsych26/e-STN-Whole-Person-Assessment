import "package:flutter/material.dart";
import "package:uuid/uuid.dart";
import "../models/profile_models.dart";
import "../storage/secure_hive.dart";

class ProfilesScreen extends StatefulWidget {
  const ProfilesScreen({super.key});

  @override
  State<ProfilesScreen> createState() => _ProfilesScreenState();
}

class _ProfilesScreenState extends State<ProfilesScreen> {
  final _uuid = const Uuid();
  final _clientName = TextEditingController();
  final _clientDob = TextEditingController();
  final _clientContact = TextEditingController();
  final _clinName = TextEditingController();
  final _clinTitle = TextEditingController();
  final _clinReg = TextEditingController();

  bool _saving = false;
  String? _loadError;

  @override
  void initState() {
    super.initState();
    try {
      final client = SecureHive.loadActiveClient();
      final clinician = SecureHive.loadActiveClinician();
      if (client != null) {
        _clientName.text = client.fullName;
        _clientDob.text = client.dobIso;
        _clientContact.text = client.contact;
      }
      if (clinician != null) {
        _clinName.text = clinician.name;
        _clinTitle.text = clinician.title;
        _clinReg.text = clinician.registration;
      }
    } catch (error) {
      _loadError = error.toString();
    }
  }

  @override
  void dispose() {
    _clientName.dispose();
    _clientDob.dispose();
    _clientContact.dispose();
    _clinName.dispose();
    _clinTitle.dispose();
    _clinReg.dispose();
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
    final clientName = _clientName.text.trim();
    final clinicianName = _clinName.text.trim();
    final dob = _clientDob.text.trim();

    if (clientName.isEmpty || clinicianName.isEmpty) {
      _message("Enter both a client name and clinician name.");
      return;
    }
    if (dob.isNotEmpty && DateTime.tryParse(dob) == null) {
      _message("Enter the date of birth in YYYY-MM-DD format.");
      return;
    }

    setState(() => _saving = true);
    try {
      // Preserve existing IDs. Re-saving a profile must not silently create
      // a different client or clinician identity.
      final existingClient = SecureHive.loadActiveClient();
      final existingClinician = SecureHive.loadActiveClinician();
      final client = ClientProfile(
        id: existingClient?.id ?? _uuid.v4(),
        fullName: clientName,
        dobIso: dob,
        contact: _clientContact.text.trim(),
      );
      final clinician = ClinicianProfile(
        id: existingClinician?.id ?? _uuid.v4(),
        name: clinicianName,
        title: _clinTitle.text.trim(),
        registration: _clinReg.text.trim(),
      );

      await SecureHive.saveActiveClient(client);
      await SecureHive.saveActiveClinician(clinician);
      _message("Profiles saved to encrypted device-local MVP storage.");
    } catch (error) {
      _message("Could not save profiles: $error");
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _clear() async {
    if (_saving) return;
    setState(() => _saving = true);
    try {
      await SecureHive.clearProfiles();
      if (!mounted) return;
      _clientName.clear();
      _clientDob.clear();
      _clientContact.clear();
      _clinName.clear();
      _clinTitle.clear();
      _clinReg.clear();
      _message("Device-local profiles cleared.");
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
        title: const Text("Profiles"),
        actions: [
          IconButton(
            icon: const Icon(Icons.delete_outline),
            tooltip: "Clear",
            onPressed: _saving ? null : _clear,
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            "Development MVP only. These profiles are stored on this device; "
            "they are not authenticated identities or production clinical records.",
          ),
          if (_loadError != null)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: Text(
                "Stored profiles could not be loaded: $_loadError",
                style: const TextStyle(color: Colors.red),
              ),
            ),
          const SizedBox(height: 12),
          const Text(
            "Client Profile",
            style: TextStyle(fontWeight: FontWeight.w700),
          ),
          TextField(
            controller: _clientName,
            decoration: const InputDecoration(labelText: "Client full name"),
          ),
          TextField(
            controller: _clientDob,
            keyboardType: TextInputType.datetime,
            decoration: const InputDecoration(labelText: "DOB (YYYY-MM-DD)"),
          ),
          TextField(
            controller: _clientContact,
            keyboardType: TextInputType.emailAddress,
            decoration: const InputDecoration(labelText: "Contact (phone/email)"),
          ),
          const SizedBox(height: 20),
          const Text(
            "Clinician Profile",
            style: TextStyle(fontWeight: FontWeight.w700),
          ),
          TextField(
            controller: _clinName,
            decoration: const InputDecoration(labelText: "Clinician name"),
          ),
          TextField(
            controller: _clinTitle,
            decoration: const InputDecoration(labelText: "Title"),
          ),
          TextField(
            controller: _clinReg,
            decoration: const InputDecoration(labelText: "Registration number"),
          ),
          const SizedBox(height: 20),
          ElevatedButton(
            onPressed: _saving ? null : _save,
            child: Text(_saving ? "Saving…" : "Save Profiles"),
          ),
        ],
      ),
    );
  }
}

import "package:flutter/material.dart";

import "clinician_services.dart";
import "record_detail_screen.dart";
import "review_queue_screen.dart";

/// Signed-in landing page: who the server says you are, and where to go next.
class ClinicianHomeScreen extends StatefulWidget {
  const ClinicianHomeScreen({super.key, required this.services});

  final ClinicianServices services;

  @override
  State<ClinicianHomeScreen> createState() => _ClinicianHomeScreenState();
}

class _ClinicianHomeScreenState extends State<ClinicianHomeScreen> {
  late Future<Map<String, dynamic>> _access;
  final _reference = TextEditingController();

  @override
  void initState() {
    super.initState();
    _access = widget.services.client.access();
  }

  @override
  void dispose() {
    _reference.dispose();
    super.dispose();
  }

  Future<void> _signOut() async {
    await widget.services.auth.signOut();
    if (mounted) Navigator.of(context).popUntil((route) => route.isFirst);
  }

  void _open(List<String> roles) {
    final id = _reference.text.trim();
    if (id.isEmpty) return;
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (_) => RecordDetailScreen(
          services: widget.services,
          assessmentId: id,
          roles: roles,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Clinician workspace"),
        actions: [
          IconButton(
            key: const ValueKey("clinician-sign-out"),
            icon: const Icon(Icons.logout),
            tooltip: "Sign out",
            onPressed: _signOut,
          ),
        ],
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _access,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Padding(
              padding: const EdgeInsets.all(16),
              child: Text(snapshot.error.toString()),
            );
          }
          final access = snapshot.data!;
          final roles = [for (final r in (access["roles"] as List? ?? [])) "$r"];
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(16),
                  child: Text(syntheticDataNotice),
                ),
              ),
              Card(
                child: ListTile(
                  leading: const Icon(Icons.badge_outlined),
                  title: Text("Signed in as ${access["subject"]}"),
                  subtitle: Text(
                    "Organisation: ${access["organisation"] ?? "not assigned"}\n"
                    "Roles: ${roles.isEmpty ? "none" : roles.join(", ")} · "
                    "MFA: ${access["mfa"] == true ? "yes" : "no"}",
                  ),
                ),
              ),
              if (roles.contains("reviewer"))
                Card(
                  child: ListTile(
                    key: const ValueKey("clinician-review-queue-entry"),
                    leading: const Icon(Icons.fact_check_outlined),
                    title: const Text("Review queue"),
                    subtitle: const Text("Submitted work awaiting clinician review"),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => ReviewQueueScreen(
                          services: widget.services,
                          roles: roles,
                        ),
                      ),
                    ),
                  ),
                ),
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text("Open an assessment by reference"),
                      TextField(
                        controller: _reference,
                        decoration: const InputDecoration(
                          labelText: "Assessment reference",
                        ),
                      ),
                      const SizedBox(height: 8),
                      OutlinedButton(
                        onPressed: () => _open(roles),
                        child: const Text("Open"),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

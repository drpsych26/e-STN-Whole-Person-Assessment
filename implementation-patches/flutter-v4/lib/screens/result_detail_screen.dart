import "package:flutter/material.dart";
import "package:share_plus/share_plus.dart";

import "../models/assessment_models.dart";
import "../models/profile_models.dart";
import "../logic/report_builder.dart";
import "../storage/secure_hive.dart";

class ResultDetailScreen extends StatelessWidget {
  final ModuleResult result;

  const ResultDetailScreen({super.key, required this.result});

  Future<void> _shareReport(BuildContext context, String report) async {
    try {
      await Share.share(report, subject: "STN Development MVP Summary");
    } catch (error) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text("Report export failed: $error")));
    }
  }

  @override
  Widget build(BuildContext context) {
    ClientProfile? client;
    ClinicianProfile? clinician;
    String? profileError;

    try {
      client = SecureHive.loadActiveClient();
      clinician = SecureHive.loadActiveClinician();
    } catch (error) {
      profileError = error.toString();
    }

    final report = ReportBuilder.buildClinicianReport(
      r: result,
      client: client,
      clinician: clinician,
    );

    return Scaffold(
      appBar: AppBar(
        title: Text("Response summary: ${result.moduleId}"),
        actions: [
          IconButton(
            icon: const Icon(Icons.ios_share),
            tooltip: "Export report",
            onPressed: () => _shareReport(context, report),
          ),
        ],
      ),
      body: Padding(
        padding: const EdgeInsets.all(16),
        child: ListView(
          children: [
            if (profileError != null)
              Text(
                "Profile data could not be loaded; report uses blank profile fields. $profileError",
                style: const TextStyle(color: Colors.red),
              ),
            SelectableText(report),
          ],
        ),
      ),
    );
  }
}

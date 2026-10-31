import "package:flutter/material.dart";
import "package:share_plus/share_plus.dart";
import "../models/assessment_models.dart";
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
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Report export failed: $error")),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final client = SecureHive.loadActiveClient();
    final clinician = SecureHive.loadActiveClinician();
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
        child: SelectableText(report),
      ),
    );
  }
}

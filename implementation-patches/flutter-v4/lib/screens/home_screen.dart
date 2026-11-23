import "package:flutter/material.dart";

import "../api/api_config.dart";
import "clinician/clinician_services.dart";
import "clinician/clinician_sign_in_screen.dart";
import "module_screen.dart";
import "results_screen.dart";
import "profiles_screen.dart";
import "whole_person_initial_assessment_screen.dart";

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key, this.apiConfig, this.clinicianServices});

  /// Defaults to the build's dart-defines. With STN_API_ENABLED off (the
  /// default) no clinician sign-in entry is shown and nothing uses the network.
  final ApiConfig? apiConfig;

  /// Test hook; defaults to the platform services for the build.
  final ClinicianServices Function(ApiConfig config)? clinicianServices;

  @override
  Widget build(BuildContext context) {
    final config = apiConfig ?? const ApiConfig.fromEnvironment();
    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Image.asset(
              "assets/brand/stn-logo-original.png",
              height: 40,
              fit: BoxFit.contain,
              semanticLabel: "Supportive Therapy Network Ltd, Rehab. Right.",
              errorBuilder: (context, error, stackTrace) => const SizedBox.shrink(),
            ),
            const SizedBox(width: 12),
            const Flexible(child: Text("Supportive Therapy Network", overflow: TextOverflow.ellipsis)),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.person),
            tooltip: "Profiles",
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const ProfilesScreen()),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.history),
            tooltip: "Results History",
            onPressed: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const ResultsScreen()),
            ),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          const Card(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text("Two assessments, one intake", style: TextStyle(fontFamily: "SourceSerif4", fontSize: 24, fontWeight: FontWeight.w600)),
                  SizedBox(height: 8),
                  Text("Run the complete STN pathway in one application. The Whole Person Initial Assessment feeds directly into the Diagnostic Assessment, with clinician review before any diagnosis is recorded."),
                  SizedBox(height: 12),
                  Text("Consent & client context → Whole Person Initial Assessment → Safety Gate → Adaptive Screening → Integrated Results → Diagnostic Assessment → Clinician Review → Formulation & Care Plan → Finalise", style: TextStyle(fontSize: 13)),
                ],
              ),
            ),
          ),
          const Card(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: Text(
                "Development MVP only. This application does not establish "
                "a diagnosis, validated score, or clinical risk disposition. "
                "Use synthetic data only until clinical, privacy, security, "
                "and governance approvals are complete.",
              ),
            ),
          ),
          if (config.enabled)
            Card(
              key: const ValueKey("clinician-sign-in-entry"),
              child: ListTile(
                leading: const Icon(Icons.verified_user_outlined),
                title: const Text("Clinician sign-in"),
                subtitle: Text(
                  config.ready
                      ? "Review queue, safety-flag acknowledgement and sign-off · synthetic data only"
                      : "Not configured in this build",
                ),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => Navigator.push(
                  context,
                  MaterialPageRoute(
                    builder: (_) => ClinicianSignInScreen(
                      services: (clinicianServices ?? ClinicianServices.platform)(config),
                    ),
                  ),
                ),
              ),
            ),
          Card(
            child: ListTile(
              leading: const Icon(Icons.assignment_outlined),
              title: const Text("Whole Person Initial Assessment"),
              subtitle: const Text(
                "Part A — 25 core intake items · synthetic-data simulation",
              ),
              trailing: const Icon(Icons.chevron_right),
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => const WholePersonInitialAssessmentScreen(),
                ),
              ),
            ),
          ),
          _tile(context, "MDD", "Depression symptom review"),
          _tile(context, "GAD", "Anxiety symptom review"),
          _tile(context, "PTSD", "Trauma symptom review"),
          _tile(context, "ADHD", "Attention and impulsivity review"),
          const Card(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text("About STN", style: TextStyle(fontFamily: "SourceSerif4", fontSize: 20, fontWeight: FontWeight.w600)),
                  SizedBox(height: 8),
                  Text(
                    "Supportive Therapy Network Limited (STN) is developing an integrated digital mental-health infrastructure platform designed to transform how individuals are assessed, clinically understood, supported, connected with appropriate services and monitored throughout their mental-health and recovery journeys.",
                  ),
                  SizedBox(height: 8),
                  Text("Technology should strengthen professional practice, not replace it. Diagnostic decisions, clinical formulation, risk management and treatment recommendations remain subject to appropriate professional judgement, clinical governance and applicable standards."),
                  SizedBox(height: 8),
                  Text("One person. One connected pathway. A more comprehensive approach to care.", style: TextStyle(fontStyle: FontStyle.italic)),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  ListTile _tile(BuildContext context, String moduleId, String title) {
    return ListTile(
      title: Text(title),
      subtitle: const Text("Interim structured screening module"),
      onTap: () => Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => ModuleScreen(moduleId: moduleId, title: title),
        ),
      ),
    );
  }
}

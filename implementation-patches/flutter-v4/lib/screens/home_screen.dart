import "package:flutter/material.dart";
import "module_screen.dart";
import "results_screen.dart";
import "profiles_screen.dart";
import "whole_person_initial_assessment_screen.dart";

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        leading: const Padding(
          padding: const EdgeInsets.all(7),
          child: CircleAvatar(
            backgroundColor: const Color(0xFFAF2CFF),
            child: const Text(
              "STN",
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.w800,
                fontSize: 11,
              ),
            ),
          ),
        ),
        title: const Text("STN Whole Person Assessment"),
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
              child: Text(
                "Development MVP only. This application does not establish "
                "a diagnosis, validated score, or clinical risk disposition. "
                "Use synthetic data only until clinical, privacy, security, "
                "and governance approvals are complete.",
              ),
            ),
          ),
          Card(
            child: ListTile(
              leading: const Icon(Icons.assignment_outlined),
              title: const Text("Whole Person Initial Assessment"),
              subtitle: const Text("Part A — 25 core intake items · synthetic-data simulation"),
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
          const Padding(
            padding: EdgeInsets.symmetric(vertical: 18, horizontal: 12),
            child: Text(
              "© 2026 Supportive Therapy Network Limited. All rights reserved in STN-owned material. Third-party components remain subject to their own licences. Development prototype — synthetic data only.",
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 11, color: Colors.white54),
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

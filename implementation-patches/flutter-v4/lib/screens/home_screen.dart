import "package:flutter/material.dart";
import "module_screen.dart";
import "results_screen.dart";
import "profiles_screen.dart";

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("STN Diagnostic Tool"),
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
        children: [
          _tile(context, "MDD", "Major Depressive Disorder (screening module)"),
          _tile(context, "GAD", "Generalised Anxiety Disorder (screening module)"),
          _tile(context, "PTSD", "PTSD / Trauma (screening module)"),
          _tile(context, "ADHD", "ADHD (screening module)"),
        ],
      ),
    );
  }

  ListTile _tile(BuildContext context, String moduleId, String title) {
    return ListTile(
      title: Text(title),
      subtitle: const Text("Structured responses • interim clinician-review flags"),
      onTap: () => Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => ModuleScreen(moduleId: moduleId, title: title),
        ),
      ),
    );
  }
}

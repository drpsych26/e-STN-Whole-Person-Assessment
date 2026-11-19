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
        title: Semantics(
          label: "Supportive Therapy Network Ltd, Rehab. Right. Diagnostic tool",
          child: Image.asset(
            "assets/brand/stn-logo-original.png",
            height: 44,
            fit: BoxFit.contain,
            alignment: Alignment.centerLeft,
            excludeFromSemantics: true,
          ),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.person),
            tooltip: "Profiles",
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ProfilesScreen())),
          ),
          IconButton(
            icon: const Icon(Icons.history),
            tooltip: "Results History",
            onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const ResultsScreen())),
          ),
        ],
      ),
      body: ListView(
        children: [
          _tile(context, "MDD", "Major Depressive Disorder (DSM gating)"),
          _tile(context, "GAD", "Generalised Anxiety Disorder"),
          _tile(context, "PTSD", "PTSD / Trauma"),
          _tile(context, "ADHD", "ADHD"),
        ],
      ),
    );
  }

  ListTile _tile(BuildContext context, String moduleId, String title) {
    return ListTile(
      title: Text(title),
      subtitle: const Text("Score + criteria gating + encrypted save"),
      onTap: () => Navigator.push(
        context,
        MaterialPageRoute(builder: (_) => ModuleScreen(moduleId: moduleId, title: title)),
      ),
    );
  }
}

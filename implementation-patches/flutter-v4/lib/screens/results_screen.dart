import "package:flutter/material.dart";
import "../storage/secure_hive.dart";
import "../models/assessment_models.dart";
import "result_detail_screen.dart";

class ResultsScreen extends StatefulWidget {
  const ResultsScreen({super.key});

  @override
  State<ResultsScreen> createState() => _ResultsScreenState();
}

class _ResultsScreenState extends State<ResultsScreen> {
  List<ModuleResult> _results = [];
  String? _loadError;

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  void _refresh() {
    try {
      final results = SecureHive.loadResults();
      if (!mounted) return;
      setState(() {
        _results = results;
        _loadError = null;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() => _loadError = error.toString());
    }
  }

  Future<void> _clear() async {
    try {
      await SecureHive.clearResults();
      _refresh();
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text("Could not clear results: $error")),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Saved Response Summaries"),
        actions: [
          IconButton(
            icon: const Icon(Icons.delete_outline),
            tooltip: "Clear",
            onPressed: _clear,
          ),
        ],
      ),
      body: _loadError != null
          ? Center(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Text("Stored results could not be read: $_loadError"),
              ),
            )
          : _results.isEmpty
              ? const Center(child: Text("No saved response summaries yet."))
              : ListView.builder(
                  itemCount: _results.length,
                  itemBuilder: (_, index) {
                    final result = _results[index];
                    return ListTile(
                      title: Text(
                        "${result.moduleId} — Response sum ${result.totalScore}",
                      ),
                      subtitle: Text(
                        "${result.completedAt.toLocal()}\n"
                        "Diagnostic criteria: Not assessed\n"
                        "${result.interpretation}",
                        maxLines: 3,
                        overflow: TextOverflow.ellipsis,
                      ),
                      trailing: result.riskFlag
                          ? const Icon(Icons.warning_amber)
                          : null,
                      onTap: () => Navigator.push(
                        context,
                        MaterialPageRoute(
                          builder: (_) => ResultDetailScreen(result: result),
                        ),
                      ).then((_) => _refresh()),
                    );
                  },
                ),
    );
  }
}

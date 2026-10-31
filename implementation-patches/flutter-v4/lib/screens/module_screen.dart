import "package:flutter/material.dart";
import "../models/assessment_models.dart";
import "../modules/mdd_module.dart";
import "../modules/gad_module.dart";
import "../modules/ptsd_module.dart";
import "../modules/adhd_module.dart";
import "../logic/scoring_engine.dart";
import "../storage/secure_hive.dart";

class ModuleScreen extends StatefulWidget {
  final String moduleId;
  final String title;

  const ModuleScreen({super.key, required this.moduleId, required this.title});

  @override
  State<ModuleScreen> createState() => _ModuleScreenState();
}

class _ModuleScreenState extends State<ModuleScreen> {
  final Map<String, Severity> _responses = {};
  final _engine = ScoringEngine();
  bool _saving = false;

  List<Question> get _questions {
    switch (widget.moduleId) {
      case "MDD":
        return mddQuestions;
      case "GAD":
        return gadQuestions;
      case "PTSD":
        return ptsdQuestions;
      case "ADHD":
        return adhdQuestions;
      default:
        return const <Question>[];
    }
  }

  @override
  Widget build(BuildContext context) {
    final questions = _questions;
    if (questions.isEmpty) {
      return Scaffold(
        appBar: AppBar(title: const Text("Assessment unavailable")),
        body: const Center(
          child: Text("This assessment module is not configured."),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: Text(widget.title)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Text(
            "Development screening only. These items are not a validated "
            "instrument and cannot establish a diagnosis or determine "
            "whether a person is safe.",
          ),
          const SizedBox(height: 12),
          const Text(
            "Rate each item: None, Mild, Moderate, Severe, or Extreme. "
            "An unanswered item is not treated as a negative response.",
          ),
          const SizedBox(height: 12),
          Text("Answered ${_responses.length} of ${questions.length} items"),
          const SizedBox(height: 8),
          ...questions.map(_questionTile),
          const SizedBox(height: 16),
          ElevatedButton(
            onPressed: _saving ? null : _scoreAndSave,
            child: Text(_saving ? "Saving…" : "Save response summary"),
          ),
        ],
      ),
    );
  }

  Widget _questionTile(Question question) {
    final current = _responses[question.id];
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              question.text,
              style: const TextStyle(fontWeight: FontWeight.w600),
            ),
            if (question.isRiskItem)
              const Padding(
                padding: EdgeInsets.only(top: 6),
                child: Text(
                  "Designated clinician-review item — a positive or unanswered "
                  "response requires direct human review.",
                  style: TextStyle(fontSize: 12),
                ),
              ),
            DropdownButton<Severity>(
              value: current,
              hint: const Text("Select response"),
              isExpanded: true,
              items: Severity.values
                  .map(
                    (severity) => DropdownMenuItem(
                      value: severity,
                      child: Text(severity.name.toUpperCase()),
                    ),
                  )
                  .toList(),
              onChanged: _saving
                  ? null
                  : (value) {
                      if (value == null) return;
                      setState(() => _responses[question.id] = value);
                    },
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _scoreAndSave() async {
    if (_saving) return;
    setState(() => _saving = true);

    try {
      final answers = _responses.entries
          .map(
            (entry) => Answer(
              questionId: entry.key,
              severity: entry.value,
            ),
          )
          .toList();
      final result = _engine.score(widget.moduleId, _questions, answers);
      await SecureHive.addResult(result);

      if (!mounted) return;
      await showDialog<void>(
        context: context,
        builder: (dialogContext) => AlertDialog(
          title: Text("${widget.moduleId} response summary"),
          content: Text(
            "Descriptive response sum: ${result.totalScore}\n"
            "Diagnostic criteria: NOT ASSESSED\n"
            "Clinician review required: ${result.riskFlag ? "YES" : "NOT FLAGGED"}\n\n"
            "${result.interpretation}\n\n"
            "Saved to encrypted local MVP storage.",
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(dialogContext),
              child: const Text("Close"),
            ),
          ],
        ),
      );
    } catch (error) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text("Could not save the response summary: $error"),
          duration: const Duration(seconds: 8),
        ),
      );
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }
}

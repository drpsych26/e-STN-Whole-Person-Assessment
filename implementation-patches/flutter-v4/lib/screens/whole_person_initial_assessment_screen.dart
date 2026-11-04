import "package:flutter/material.dart";
import "../storage/secure_hive.dart";
import "../models/core_intake.dart";
import "profiles_screen.dart";

class WholePersonInitialAssessmentScreen extends StatefulWidget {
  const WholePersonInitialAssessmentScreen({super.key});
  @override
  State<WholePersonInitialAssessmentScreen> createState() => _WholePersonInitialAssessmentScreenState();
}

class _WholePersonInitialAssessmentScreenState extends State<WholePersonInitialAssessmentScreen> {
  final TextEditingController _caseIdController = TextEditingController();
  final Map<int, int> _answers = <int, int>{};
  List<Map<String, dynamic>> _drafts = <Map<String, dynamic>>[];
  String? _draftId;
  String? _createdAt;
  bool _simulationAcknowledged = false;
  bool _saving = false;
  bool _legacyProfileBlocked = false;

  @override
  void initState() {
    super.initState();
    _refreshDrafts();
  }

  @override
  void dispose() {
    _caseIdController.dispose();
    super.dispose();
  }

  void _showMessage(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(message), duration: const Duration(seconds: 5)),
    );
  }

  Future<void> _refreshDrafts() async {
    try {
      final client = SecureHive.loadActiveClient();
      final clinician = SecureHive.loadActiveClinician();
      final legacyProfile =
          (client != null && !CoreIntakeRules.isSyntheticCaseId(client.id)) ||
          (clinician != null &&
              !CoreIntakeRules.isSyntheticTesterAlias(clinician.name));
      final drafts = SecureHive.loadWholePersonDrafts();
      if (mounted) {
        setState(() {
          _drafts = drafts;
          _legacyProfileBlocked = legacyProfile;
        });
      }
    } catch (error) {
      if (mounted) {
        setState(() => _legacyProfileBlocked = true);
        _showMessage("Could not verify local profile safety; UAT saving is blocked: $error");
      }
    }
  }

  Future<void> _openDraft(String id) async {
    try {
      final draft = SecureHive.loadWholePersonDraft(id);
      if (draft == null) {
        _showMessage("That saved draft is no longer available.");
        await _refreshDrafts();
        return;
      }
      final rawAnswers = Map<String, dynamic>.from(draft["answers"] as Map? ?? {});
      setState(() {
        _draftId = id;
        _createdAt = draft["createdAt"] as String?;
        _caseIdController.text = draft["syntheticCaseId"] as String? ?? "";
        _simulationAcknowledged = draft["simulationAcknowledged"] == true;
        _answers
          ..clear()
          ..addAll({
            for (final entry in rawAnswers.entries)
              int.parse(entry.key): (entry.value as num).toInt(),
          });
      });
      _showMessage("Synthetic draft reopened.");
    } catch (error) {
      _showMessage("Could not reopen the saved draft: $error");
    }
  }

  void _startNewDraft() {
    setState(() {
      _draftId = null;
      _createdAt = null;
      _caseIdController.clear();
      _simulationAcknowledged = false;
      _answers.clear();
    });
  }

  Future<bool> _saveDraft({bool completed = false}) async {
    if (_saving) return false;
    if (_legacyProfileBlocked) {
      _showMessage("Clear legacy non-synthetic profile data in Profiles before using this UAT screen.");
      return false;
    }
    final caseId = _caseIdController.text.trim();
    if (!CoreIntakeRules.isSyntheticCaseId(caseId)) {
      _showMessage("Use a synthetic test ID beginning with SYNTH-. Real client identifiers are blocked.");
      return false;
    }
    if (!_simulationAcknowledged) {
      _showMessage("Acknowledge the non-clinical simulation boundary before saving.");
      return false;
    }
    if (!CoreIntakeRules.areAnswersValid(_answers)) {
      _showMessage("One or more responses are invalid. Review the answers before saving.");
      return false;
    }
    if (completed && !CoreIntakeRules.isComplete(_answers)) {
      _showMessage("Answer all 25 core items before completing this synthetic test.");
      return false;
    }

    setState(() => _saving = true);
    try {
      final now = DateTime.now().toUtc().toIso8601String();
      final id = _draftId ?? DateTime.now().microsecondsSinceEpoch.toString();
      final createdAt = _createdAt ?? now;
      final draft = <String, dynamic>{
        "id": id,
        "syntheticCaseId": caseId,
        "createdAt": createdAt,
        "updatedAt": now,
        "completed": completed,
        "simulationAcknowledged": _simulationAcknowledged,
        "sourceVersion": "STN-INITIAL-1.0.0",
        "answers": {for (final entry in _answers.entries) entry.key.toString(): entry.value},
        "unresolvedSafetyItems": CoreIntakeRules.unresolvedSafetyItems(_answers),
      };
      await SecureHive.saveWholePersonDraft(draft);
      if (!mounted) return false;
      setState(() {
        _draftId = id;
        _createdAt = createdAt;
      });
      await _refreshDrafts();
      _showMessage(completed
          ? "Synthetic core intake saved as a completed simulation."
          : "Synthetic draft saved locally in encrypted demo storage.");
      return true;
    } catch (error) {
      if (mounted) _showMessage("Draft could not be saved: $error");
      return false;
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _completeAssessment() async {
    final saved = await _saveDraft(completed: true);
    if (!saved || !mounted) return;
    final unresolved = CoreIntakeRules.unresolvedSafetyItems(_answers);
    await showDialog<void>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(unresolved.isEmpty ? "Core intake recorded" : "Human review required"),
        content: Text(unresolved.isEmpty
            ? "No positive responses were recorded for the safety-tagged core items. This is not a safety clearance, risk assessment or crisis disposition."
            : "Safety-tagged items requiring human review or clarification: ${unresolved.join(", ")}. This simulation does not contact, assign or notify a clinician and does not create a handover."),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text("Close")),
        ],
      ),
    );
  }

  Future<void> _deleteDraft(String id) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: const Text("Delete synthetic draft?"),
        content: const Text("This permanently removes the selected local test draft from this device."),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext, false), child: const Text("Cancel")),
          TextButton(onPressed: () => Navigator.pop(dialogContext, true), child: const Text("Delete")),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await SecureHive.deleteWholePersonDraft(id);
      if (mounted && _draftId == id) _startNewDraft();
      await _refreshDrafts();
      _showMessage("Synthetic draft deleted.");
    } catch (error) {
      _showMessage("Draft could not be deleted: $error");
    }
  }

  Widget _savedDraftsPanel() {
    return Card(
      child: ExpansionTile(
        title: Text("Saved synthetic drafts (${_drafts.length})"),
        subtitle: const Text("Stored on this device only"),
        children: _drafts.isEmpty
            ? const [ListTile(title: Text("No saved drafts yet."))]
            : _drafts.map((draft) {
                final id = draft["id"] as String;
                final caseId = draft["syntheticCaseId"] as String? ?? id;
                final completed = draft["completed"] == true;
                return ListTile(
                  title: Text(caseId),
                  subtitle: Text(completed ? "Completed simulation" : "Draft"),
                  leading: Icon(completed ? Icons.assignment_turned_in : Icons.edit_note),
                  onTap: () => _openDraft(id),
                  trailing: IconButton(
                    tooltip: "Delete synthetic draft",
                    icon: const Icon(Icons.delete_outline),
                    onPressed: () => _deleteDraft(id),
                  ),
                );
              }).toList(),
      ),
    );
  }

  Widget _questionCard(CoreIntakeQuestion question) {
    final selected = _answers[question.number];
    return Card(
      key: ValueKey("core-item-${question.number}"),
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                CircleAvatar(radius: 14, child: Text(question.number.toString())),
                const SizedBox(width: 10),
                Expanded(child: Text(question.text, style: const TextStyle(fontWeight: FontWeight.w600))),
              ],
            ),
            if (question.safetyTagged)
              const Padding(
                padding: EdgeInsets.only(top: 8),
                child: Text(
                  "Safety-tagged item in the supplied paper pilot. This is not a risk score.",
                  style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600),
                ),
              ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: List<Widget>.generate(5, (value) => Tooltip(
                message: "$value — ${coreIntakeResponseLabels[value]}",
                child: ChoiceChip(
                  label: Text(value.toString()),
                  selected: selected == value,
                  onSelected: _saving ? null : (isSelected) {
                    if (!isSelected) return;
                    setState(() => _answers[question.number] = value);
                  },
                ),
              )),
            ),
            if (selected != null)
              Padding(
                padding: const EdgeInsets.only(top: 5),
                child: Text(
                  "$selected — ${coreIntakeResponseLabels[selected]}",
                  style: Theme.of(context).textTheme.bodySmall,
                ),
              ),
          ],
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final answered = CoreIntakeRules.answeredCount(_answers);
    final unresolved = CoreIntakeRules.unresolvedSafetyItems(_answers);
    return Scaffold(
      appBar: AppBar(
        title: const Text("Whole Person Initial Assessment"),
        actions: [
          IconButton(
            tooltip: "Start new synthetic draft",
            onPressed: _saving ? null : _startNewDraft,
            icon: const Icon(Icons.add),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(12),
        children: [
          Card(
            color: Theme.of(context).colorScheme.errorContainer,
            child: const Padding(
              padding: EdgeInsets.all(14),
              child: Text(
                "PRIVATE DEVELOPMENT SIMULATION — SYNTHETIC DATA ONLY. "
                "This screen implements Part A of the supplied STN-INITIAL-1.0.0 paper pilot. "
                "It is not approved for real patients, clinical care, diagnosis, triage or risk clearance. "
                "Local encrypted storage is not a production clinical record.",
                style: TextStyle(fontWeight: FontWeight.w600),
              ),
            ),
          ),
          if (_legacyProfileBlocked)
            Card(
              color: Theme.of(context).colorScheme.errorContainer,
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "Legacy profile data must be cleared before UAT saving is enabled.",
                      style: TextStyle(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 8),
                    const Text("The app will not use or display legacy non-synthetic profiles in this assessment."),
                    OutlinedButton(
                      onPressed: () async {
                        await Navigator.push(
                          context,
                          MaterialPageRoute(builder: (_) => const ProfilesScreen()),
                        );
                        await _refreshDrafts();
                      },
                      child: const Text("Open synthetic profiles and clear legacy data"),
                    ),
                  ],
                ),
              ),
            ),
          _savedDraftsPanel(),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("Synthetic test case", style: TextStyle(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _caseIdController,
                    decoration: const InputDecoration(
                      labelText: "Synthetic case ID",
                      hintText: "SYNTH-TEST-001",
                      helperText: "Must start with SYNTH-. Real client identifiers are rejected.",
                      border: OutlineInputBorder(),
                    ),
                    textCapitalization: TextCapitalization.characters,
                  ),
                  CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    value: _simulationAcknowledged,
                    onChanged: _saving ? null : (value) => setState(() => _simulationAcknowledged = value ?? false),
                    title: const Text("I understand this is a non-clinical synthetic-data simulation."),
                    controlAffinity: ListTileControlAffinity.leading,
                  ),
                  Text("Progress: $answered / 25 answered", style: Theme.of(context).textTheme.titleSmall),
                  LinearProgressIndicator(value: answered / 25),
                ],
              ),
            ),
          ),
          const Card(
            child: Padding(
              padding: EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text("Response scale", style: TextStyle(fontWeight: FontWeight.bold)),
                  SizedBox(height: 6),
                  Text("0 — Not at all / no"),
                  Text("1 — A little / occasionally"),
                  Text("2 — Moderately / sometimes"),
                  Text("3 — A lot / often"),
                  Text("4 — Extreme / nearly always"),
                  SizedBox(height: 6),
                  Text("Past 2–4 weeks unless stated otherwise. The supplied paper pilot says safety items are interpreted independently from symptom burden."),
                ],
              ),
            ),
          ),
          ...coreIntakeQuestions.map(_questionCard),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text("Safety-tagged item review", style: TextStyle(fontWeight: FontWeight.bold)),
                  const SizedBox(height: 6),
                  Text(unresolved.isEmpty
                      ? "No positive or missing safety-tagged core responses. This is not a safety clearance."
                      : "Human review / clarification required for item(s): ${unresolved.join(", ")}."),
                  const SizedBox(height: 6),
                  const Text("This prototype does not calculate a safety tier, initiate a crisis response, contact a clinician or record an acknowledged handover."),
                  const SizedBox(height: 10),
                  const Text("Adaptive follow-up routing and the remaining paper-pilot sections are not yet implemented in this Flutter screen. Do not infer routing from these descriptive responses."),
                ],
              ),
            ),
          ),
          Wrap(
            spacing: 10,
            runSpacing: 10,
            children: [
              OutlinedButton.icon(
                onPressed: _saving ? null : () => _saveDraft(),
                icon: const Icon(Icons.save_outlined),
                label: Text(_saving ? "Saving…" : "Save draft"),
              ),
              FilledButton.icon(
                onPressed: _saving || !CoreIntakeRules.isComplete(_answers) ? null : _completeAssessment,
                icon: const Icon(Icons.check_circle_outline),
                label: const Text("Complete simulation"),
              ),
            ],
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

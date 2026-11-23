import "dart:convert";

import "package:flutter/material.dart";

import "../../api/api_client.dart";
import "clinician_services.dart";

/// One assessment: metadata, safety flags and the workflow actions the server
/// may allow. The server enforces every rule (author, reviewer, separation of
/// duties, flag acknowledgement before review); the buttons only offer them.
class RecordDetailScreen extends StatefulWidget {
  const RecordDetailScreen({
    super.key,
    required this.services,
    required this.assessmentId,
    required this.roles,
    this.summary,
  });

  final ClinicianServices services;
  final String assessmentId;
  final List<String> roles;

  /// Queue metadata, shown when the full record is not yet readable
  /// (a reviewer reads the payload only after starting the review).
  final Map<String, dynamic>? summary;

  @override
  State<RecordDetailScreen> createState() => _RecordDetailScreenState();
}

class _RecordDetailScreenState extends State<RecordDetailScreen> {
  Map<String, dynamic>? _record;
  Map<String, dynamic>? _meta;
  List<Map<String, dynamic>> _flags = const [];
  String? _error;
  bool _loading = true;
  bool _busy = false;

  ApiClient get _api => widget.services.client;
  String get _id => widget.assessmentId;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    Map<String, dynamic>? record;
    Map<String, dynamic>? meta = widget.summary;
    List<Map<String, dynamic>> flags = const [];
    String? error;
    try {
      record = await _api.assessment(_id);
      meta = record;
      flags = [
        for (final f in (record["safety_flags"] as List? ?? const []))
          Map<String, dynamic>.from(f as Map),
      ];
    } on ApiException catch (e) {
      if (e.notFound && meta != null) {
        try {
          flags = await _api.safetyFlags(_id);
        } on ApiException catch (inner) {
          error = inner.message;
        }
      } else {
        error = e.message;
      }
    } catch (e) {
      error = e.toString();
    }
    if (!mounted) return;
    setState(() {
      _record = record;
      _meta = meta;
      _flags = flags;
      _error = error;
      _loading = false;
    });
  }

  Future<void> _act(Future<Object?> Function() action, String done) async {
    setState(() => _busy = true);
    try {
      await action();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(done)));
      }
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(e.toString())));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<bool> _confirm(String title, String body, String action) async {
    final result = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: Text(body),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text("Cancel")),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: Text(action)),
        ],
      ),
    );
    return result ?? false;
  }

  Future<String?> _ask(String title, String label, {bool required = true}) async {
    final controller = TextEditingController();
    final result = await showDialog<String>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: TextField(
          key: const ValueKey("record-dialog-input"),
          controller: controller,
          maxLines: 3,
          decoration: InputDecoration(labelText: label),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context), child: const Text("Cancel")),
          FilledButton(
            onPressed: () {
              final text = controller.text.trim();
              if (required && text.isEmpty) return;
              Navigator.pop(context, text);
            },
            child: const Text("Continue"),
          ),
        ],
      ),
    );
    controller.dispose();
    return result;
  }

  Future<void> _acknowledge(Map<String, dynamic> flag) async {
    final ok = await _confirm(
      "Acknowledge safety flag",
      "Acknowledging records your name and the time against flag "
          "'${flag["code"]}'. It is not a risk assessment and triggers no "
          "automatic action. Follow the STN safety escalation procedure.",
      "Acknowledge",
    );
    if (ok) {
      await _act(() => _api.acknowledgeFlag(_id, "${flag["id"]}"), "Flag acknowledged.");
    }
  }

  Future<void> _submit() async {
    final codes = await _ask("Submit for review", "Safety flag codes (optional, comma-separated)",
        required: false);
    if (codes == null) return;
    final flags = [
      for (final c in codes.split(",")) if (c.trim().isNotEmpty) c.trim(),
    ];
    await _act(() => _api.submit(_id, flags), "Submitted for review.");
  }

  Future<void> _return() async {
    final reason = await _ask("Return for changes", "Reason (required)");
    if (reason == null || reason.isEmpty) return;
    await _act(() => _api.returnForChanges(_id, reason), "Returned to the author.");
  }

  Future<void> _signOff() async {
    final hash = "${_meta?["content_hash"] ?? ""}";
    final ok = await _confirm(
      "Sign off",
      "You are signing off the content you reviewed (SHA-256 $hash). "
          "Signed-off records cannot be changed; corrections become new versions.",
      "Sign off",
    );
    if (ok) {
      await _act(() => _api.signOff(_id, hash), "Signed off.");
    }
  }

  @override
  Widget build(BuildContext context) {
    final meta = _meta;
    final state = "${meta?["state"] ?? ""}";
    final pending = _flags.where((f) => f["acknowledged_by"] == null).length;
    final isReviewer = widget.roles.contains("reviewer");
    final isClinician = widget.roles.contains("clinician");
    return Scaffold(
      appBar: AppBar(title: const Text("Assessment")),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                const Card(child: Padding(padding: EdgeInsets.all(16), child: Text(syntheticDataNotice))),
                if (_error != null)
                  Padding(
                    padding: const EdgeInsets.symmetric(vertical: 8),
                    child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                  ),
                if (meta != null)
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text("State: $state", key: const ValueKey("record-state")),
                          Text("Form: ${meta["form_id"]} · ${meta["form_version"]} · version ${meta["version"]}"),
                          if (meta["content_hash"] != null) SelectableText("Content SHA-256: ${meta["content_hash"]}"),
                          if (meta["reviewer_sub"] != null) Text("Reviewer: ${meta["reviewer_sub"]}"),
                          if (meta["signed_off_by"] != null)
                            Text("Signed off by ${meta["signed_off_by"]} at ${meta["signed_off_at"]}"),
                        ],
                      ),
                    ),
                  ),
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text("Safety flags (${_flags.length})", style: const TextStyle(fontWeight: FontWeight.w600)),
                        if (_flags.isEmpty) const Text("None raised at submission."),
                        for (final flag in _flags)
                          ListTile(
                            key: ValueKey("flag-${flag["id"]}"),
                            contentPadding: EdgeInsets.zero,
                            title: Text("${flag["code"]}"),
                            subtitle: Text(flag["acknowledged_by"] == null
                                ? "Raised by ${flag["raised_by"]} · not yet acknowledged"
                                : "Acknowledged by ${flag["acknowledged_by"]} at ${flag["acknowledged_at"]}"),
                            trailing: flag["acknowledged_by"] == null
                                ? TextButton(
                                    key: ValueKey("acknowledge-${flag["id"]}"),
                                    onPressed: _busy ? null : () => _acknowledge(flag),
                                    child: const Text("Acknowledge"),
                                  )
                                : const Icon(Icons.check),
                          ),
                      ],
                    ),
                  ),
                ),
                if (_record != null && _record!["payload"] != null)
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: SelectableText(
                        const JsonEncoder.withIndent("  ").convert(_record!["payload"]),
                        style: const TextStyle(fontFamily: "monospace", fontSize: 12),
                      ),
                    ),
                  ),
                const SizedBox(height: 8),
                if (isClinician && state == "draft")
                  FilledButton(
                    key: const ValueKey("action-submit"),
                    onPressed: _busy ? null : _submit,
                    child: const Text("Submit for review"),
                  ),
                if (isReviewer && state == "submitted") ...[
                  FilledButton(
                    key: const ValueKey("action-start-review"),
                    onPressed: _busy || pending > 0
                        ? null
                        : () => _act(() => _api.startReview(_id), "Review started."),
                    child: const Text("Start review"),
                  ),
                  if (pending > 0)
                    const Padding(
                      padding: EdgeInsets.only(top: 8),
                      child: Text("Every safety flag must be acknowledged before review can start."),
                    ),
                ],
                if (isReviewer && state == "in_review") ...[
                  OutlinedButton(
                    key: const ValueKey("action-return"),
                    onPressed: _busy ? null : _return,
                    child: const Text("Return for changes"),
                  ),
                  const SizedBox(height: 8),
                  FilledButton(
                    key: const ValueKey("action-sign-off"),
                    onPressed: _busy ? null : _signOff,
                    child: const Text("Sign off"),
                  ),
                ],
              ],
            ),
    );
  }
}

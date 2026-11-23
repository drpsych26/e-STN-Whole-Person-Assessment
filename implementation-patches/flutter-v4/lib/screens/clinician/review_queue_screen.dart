import "package:flutter/material.dart";

import "clinician_services.dart";
import "record_detail_screen.dart";

class ReviewQueueScreen extends StatefulWidget {
  const ReviewQueueScreen({super.key, required this.services, required this.roles});

  final ClinicianServices services;
  final List<String> roles;

  @override
  State<ReviewQueueScreen> createState() => _ReviewQueueScreenState();
}

class _ReviewQueueScreenState extends State<ReviewQueueScreen> {
  late Future<List<Map<String, dynamic>>> _queue;

  @override
  void initState() {
    super.initState();
    _queue = widget.services.client.reviewQueue();
  }

  void _reload() => setState(() => _queue = widget.services.client.reviewQueue());

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text("Review queue"),
        actions: [
          IconButton(icon: const Icon(Icons.refresh), tooltip: "Refresh", onPressed: _reload),
        ],
      ),
      body: FutureBuilder<List<Map<String, dynamic>>>(
        future: _queue,
        builder: (context, snapshot) {
          if (snapshot.connectionState != ConnectionState.done) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return Padding(
              padding: const EdgeInsets.all(16),
              child: Text(snapshot.error.toString()),
            );
          }
          final items = snapshot.data!;
          if (items.isEmpty) {
            return const Center(child: Text("Nothing is waiting for review."));
          }
          return ListView.builder(
            itemCount: items.length,
            itemBuilder: (context, index) {
              final item = items[index];
              final pending = (item["unacknowledged_safety_flags"] as num?)?.toInt() ?? 0;
              return Card(
                child: ListTile(
                  key: ValueKey("queue-item-${item["id"]}"),
                  title: Text("${item["form_id"]} · ${item["form_version"]}"),
                  subtitle: Text(
                    "State: ${item["state"]} · version ${item["version"]}\n"
                    "Submitted: ${item["submitted_at"] ?? "—"}",
                  ),
                  trailing: pending > 0
                      ? Chip(label: Text("$pending flag${pending == 1 ? "" : "s"} to acknowledge"))
                      : const Icon(Icons.chevron_right),
                  onTap: () async {
                    await Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => RecordDetailScreen(
                          services: widget.services,
                          assessmentId: "${item["id"]}",
                          roles: widget.roles,
                          summary: item,
                        ),
                      ),
                    );
                    _reload();
                  },
                ),
              );
            },
          );
        },
      ),
    );
  }
}

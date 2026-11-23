import "package:flutter/material.dart";

import "clinician_home_screen.dart";
import "clinician_services.dart";

class ClinicianSignInScreen extends StatefulWidget {
  const ClinicianSignInScreen({super.key, required this.services});

  final ClinicianServices services;

  @override
  State<ClinicianSignInScreen> createState() => _ClinicianSignInScreenState();
}

class _ClinicianSignInScreenState extends State<ClinicianSignInScreen> {
  bool _busy = false;
  String? _error;

  Future<void> _signIn() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await widget.services.auth.signIn();
      if (!mounted) return;
      await Navigator.of(context).pushReplacement(
        MaterialPageRoute(
          builder: (_) => ClinicianHomeScreen(services: widget.services),
        ),
      );
    } catch (error) {
      if (mounted) setState(() => _error = error.toString());
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final config = widget.services.config;
    return Scaffold(
      appBar: AppBar(title: const Text("Clinician sign-in")),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          const Card(
            child: Padding(
              padding: EdgeInsets.all(16),
              child: Text(syntheticDataNotice),
            ),
          ),
          if (!config.ready)
            Card(
              key: const ValueKey("clinician-sign-in-not-configured"),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "Clinician sign-in is not configured in this build.",
                      style: TextStyle(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 8),
                    for (final problem in config.problems) Text("• $problem"),
                  ],
                ),
              ),
            )
          else ...[
            const Padding(
              padding: EdgeInsets.symmetric(vertical: 12),
              child: Text(
                "You sign in on your organisation's sign-in page in the system "
                "browser. The STN app never sees your password. Multi-factor "
                "authentication is required.",
              ),
            ),
            FilledButton.icon(
              key: const ValueKey("clinician-sign-in-button"),
              onPressed: _busy ? null : _signIn,
              icon: const Icon(Icons.login),
              label: Text(_busy ? "Signing in…" : "Sign in"),
            ),
          ],
          if (_error != null)
            Padding(
              padding: const EdgeInsets.only(top: 12),
              child: Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ),
        ],
      ),
    );
  }
}

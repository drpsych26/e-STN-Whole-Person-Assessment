from pathlib import Path

root = Path(__file__).resolve().parents[2] / "flutter/source/supportive_therapy_network_v4"
replacements = {
    "lib/screens/home_screen.dart": [
        ('body: ListView(\n        children: [', 'body: ListView(\n        children: [\n          const Card(child: Padding(padding: EdgeInsets.all(16), child: Text("DEVELOPMENT PROTOTYPE — SYNTHETIC DATA ONLY. Local encrypted storage is not authentication or a secure multi-user clinical record. Do not enter real client information. This app does not provide a diagnosis, clinical risk assessment or crisis disposition.", style: TextStyle(fontWeight: FontWeight.w600)))),'),
        ('title: const Text("STN Diagnostic Tool")', 'title: const Text("STN Assessment Prototype")'),
        ('subtitle: const Text("Score + criteria gating + encrypted save")', 'subtitle: const Text("Descriptive response summary · local encrypted demo save")'),
    ],
    "lib/screens/module_screen.dart": [
        ('const Text("Rate each item (0–4): 0 None, 1 Mild, 2 Moderate, 3 Severe, 4 Extreme."),',
         'const Text("Development-only response ratings. These items are not verified as validated instruments and must not be used to diagnose or determine risk."),'),
        ('onPressed: _responses.length < questions.length ? null : _scoreAndSave,',
         'onPressed: _scoreAndSave,'),
        ('child: const Text("Score + Save (Encrypted)"),',
         'child: const Text("Save draft / submit for clinician review"),'),
        ('"Criteria Met: ${result.criteriaMet ? "YES" : "NO"}\\n"',
         '"Diagnostic criteria: NOT EVALUATED (not implemented or validated)\\n"'),
        ('"Risk Flag: ${result.riskFlag ? "YES" : "NO"}\\n\\n"',
         '"Additional clinician review flag: ${result.riskFlag ? "YES" : "NO"}\\nA NO flag does not establish safety or determine crisis disposition.\\n\\n"'),
        ('"Saved (encrypted) to Results History."',
         '"Saved to encrypted on-device demo history. This is not an authenticated clinical record."'),
    ],
    "lib/screens/results_screen.dart": [
        ('Criteria: ${r.criteriaMet ? "Met" : "Not met"}',
         'Diagnostic criteria: not evaluated'),
        ('Score ${r.totalScore}', 'Descriptive sum ${r.totalScore}'),
    ],
    "lib/logic/report_builder.dart": [
        ('b.writeln("Criteria Met (gating): ${r.criteriaMet ? "YES" : "NO"}");',
         'b.writeln("Diagnostic criteria: NOT EVALUATED (not implemented or validated)");'),
        ('b.writeln("Risk Flag: ${r.riskFlag ? "YES" : "NO"}");',
         'b.writeln("Additional clinician review flag: ${r.riskFlag ? "YES" : "NO"}");\n    b.writeln("A NO flag does not establish safety or determine crisis disposition.");'),
        ('b.writeln("This is an MVP draft output. It supports—but does not replace—professional clinical judgement.");',
         'b.writeln("This is a development prototype with unvalidated question sets. It is not a diagnostic instrument or clinical record.");\n    b.writeln("The descriptive response-severity sum is not a validated instrument score.");'),
    ],
}
for relative, pairs in replacements.items():
    path = root / relative
    text = path.read_text()
    for old, new in pairs:
        if old not in text:
            raise SystemExit(f"Expected source text not found in {relative}: {old}")
        text = text.replace(old, new)
    path.write_text(text)
print("Applied conservative UI/report wording and partial-assessment review access.")

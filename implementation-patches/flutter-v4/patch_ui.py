from pathlib import Path

root = Path(__file__).resolve().parents[2] / "flutter/source/supportive_therapy_network_v4"
replacements = {
    "lib/main.dart": [
        ('theme: ThemeData(useMaterial3: true),',
         'theme: ThemeData(\n        useMaterial3: true,\n        brightness: Brightness.dark,\n        colorScheme: ColorScheme.fromSeed(\n          seedColor: const Color(0xFFAF2CFF),\n          brightness: Brightness.dark,\n        ),\n        scaffoldBackgroundColor: const Color(0xFF08070A),\n        fontFamily: "sans-serif",\n        appBarTheme: const AppBarTheme(\n          backgroundColor: Color(0xFF08070A),\n          foregroundColor: Colors.white,\n          centerTitle: false,\n          elevation: 0,\n        ),\n        cardColor: const Color(0xFF151219),\n      ),'),
    ],
    "lib/screens/home_screen.dart": [
        ('body: ListView(\n        children: [', 'body: ListView(\n        children: [\n          const Card(child: Padding(padding: EdgeInsets.all(16), child: Text("DEVELOPMENT PROTOTYPE — SYNTHETIC DATA ONLY. Local encrypted storage is not authentication or a secure multi-user clinical record. Do not enter real client information. This app does not provide a diagnosis, clinical risk assessment or crisis disposition.", style: TextStyle(fontWeight: FontWeight.w600)))),'),
        ('title: const Text("STN Diagnostic Tool")', 'leading: Padding(padding: const EdgeInsets.all(7), child: CircleAvatar(backgroundColor: const Color(0xFFAF2CFF), child: const Text("STN", style: TextStyle(color: Colors.white, fontWeight: FontWeight.w800, fontSize: 11)))), title: const Text("STN Whole Person Assessment")'),
        ('subtitle: const Text("Score + criteria gating + encrypted save")', 'subtitle: const Text("Descriptive response summary · local encrypted demo save")'),
        ('_tile(context, "MDD", "Major Depressive Disorder (DSM gating)")', '_tile(context, "MDD", "Depression symptom domain (unvalidated prototype items)")'),
        ('_tile(context, "GAD", "Generalised Anxiety Disorder")', '_tile(context, "GAD", "Anxiety symptom domain (unvalidated prototype items)")'),
        ('_tile(context, "PTSD", "PTSD / Trauma")', '_tile(context, "PTSD", "Trauma symptom domain (unvalidated prototype items)")'),
        ('_tile(context, "ADHD", "ADHD")', '_tile(context, "ADHD", "Attention symptom domain (unvalidated prototype items)")'),
        ('_tile(context, "ADHD", "Attention symptom domain (unvalidated prototype items)"),',
         '_tile(context, "ADHD", "Attention symptom domain (unvalidated prototype items)"),\n          const Padding(padding: EdgeInsets.symmetric(vertical: 18, horizontal: 12), child: Text("© 2026 Supportive Therapy Network Limited. All rights reserved in STN-owned material. Third-party components remain subject to their own licences. Development prototype — synthetic data only.", textAlign: TextAlign.center, style: TextStyle(fontSize: 11, color: Colors.white54))),'),
    ],
    "lib/screens/module_screen.dart": [
        ('const Text("Rate each item (0–4): 0 None, 1 Mild, 2 Moderate, 3 Severe, 4 Extreme."),',
         'const Text("Development-only response ratings. These items are not verified as validated instruments and must not be used to diagnose or determine risk."),'),
        ('onPressed: _responses.length < questions.length ? null : _scoreAndSave,',
         'onPressed: _scoreAndSave,'),
        ('child: const Text("Score + Save (Encrypted)"),',
         'child: const Text("Save draft (local demo)"),'),
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

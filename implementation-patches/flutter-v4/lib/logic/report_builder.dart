import "../models/assessment_models.dart";
import "../models/profile_models.dart";

class ReportBuilder {
  static String buildClinicianReport({
    required ModuleResult r,
    required ClientProfile? client,
    required ClinicianProfile? clinician,
  }) {
    final buffer = StringBuffer();

    buffer.writeln("SUPPORTIVE THERAPY NETWORK LTD");
    buffer.writeln("Clinical Module Summary — Development MVP");
    buffer.writeln(
      "------------------------------------------------------------",
    );
    buffer.writeln("Client: ${client?.fullName ?? "[Not set]"}");
    buffer.writeln("Client DOB: ${client?.dobIso ?? "[Not set]"}");
    buffer.writeln("Client Contact: ${client?.contact ?? "[Not set]"}");
    buffer.writeln();
    buffer.writeln("Clinician: ${clinician?.name ?? "[Not set]"}");
    buffer.writeln("Title: ${clinician?.title ?? "[Not set]"}");
    buffer.writeln("Registration: ${clinician?.registration ?? "[Not set]"}");
    buffer.writeln(
      "------------------------------------------------------------",
    );
    buffer.writeln("Module: ${r.moduleId}");
    buffer.writeln("Completed: ${r.completedAt.toLocal()}");
    buffer.writeln("Descriptive response sum: ${r.totalScore}");
    buffer.writeln("Diagnostic criteria: NOT ASSESSED");
    buffer.writeln(
      "Clinician review required: ${r.riskFlag ? "YES" : "NOT FLAGGED"}",
    );
    buffer.writeln();
    buffer.writeln("Interim workflow note:");
    buffer.writeln(r.interpretation);
    buffer.writeln();
    buffer.writeln("Item response values (0–4):");
    r.itemScores.forEach(
      (questionId, value) => buffer.writeln("- $questionId: $value"),
    );
    buffer.writeln();
    buffer.writeln("Clinical and technical limitation:");
    buffer.writeln(
      "This is an unvalidated development MVP summary. It is not a "
      "validated instrument score, diagnosis, or risk assessment and does "
      "not replace professional clinical judgement.",
    );
    buffer.writeln(
      "Do not use as a clinical record or for decisions about care until "
      "clinical governance, instrument permissions, privacy, security, "
      "safety workflow and validation approvals are complete.",
    );
    return buffer.toString();
  }
}

import "../models/assessment_models.dart";

/// Conservative interim engine for the unvalidated STN MVP.
///
/// This deliberately does NOT calculate a diagnostic score, apply generic
/// severity bands, or claim diagnostic criteria have been met. Until every
/// instrument and rule is traced to an approved source, the numeric total is
/// only a descriptive sum of entered response severities.
class ScoringEngine {
  ModuleResult score(String moduleId, List<Question> questions, List<Answer> answers) {
    if (questions.isEmpty) {
      throw ArgumentError('Unknown or unconfigured assessment module: $moduleId');
    }

    final questionIds = questions.map((q) => q.id).toSet();
    final seen = <String>{};
    for (final answer in answers) {
      if (!questionIds.contains(answer.questionId)) {
        throw ArgumentError('Unknown question ID: ${answer.questionId}');
      }
      if (!seen.add(answer.questionId)) {
        throw ArgumentError('Duplicate answer for question: ${answer.questionId}');
      }
    }

    final itemScores = <String, int>{};
    for (final answer in answers) {
      itemScores[answer.questionId] = severityToScore(answer.severity);
    }
    final total = itemScores.values.fold<int>(0, (sum, value) => sum + value);
    final incomplete = questions.any((question) => !seen.contains(question.id));

    // Missing/ambiguous safety information is never interpreted as negative.
    // Positive responses to items marked for review also require a clinician.
    final safetyReviewRequired = incomplete || questions.any((question) {
      if (!question.isRiskItem) return false;
      Answer? answer;
      for (final candidate in answers) {
        if (candidate.questionId == question.id) answer = candidate;
      }
      return answer == null || answer.severity != Severity.none;
    });

    final interpretation = (safetyReviewRequired
        ? 'Clinician review required: assessment is incomplete and/or a designated review item is positive or unanswered. This flag is not a risk assessment or crisis disposition. '
        : 'No review flag triggered by this interim rule set; this is not proof of safety. ') +
        'The response-severity sum is descriptive only, not a validated instrument score or diagnosis. Diagnostic criteria are not assessed.';

    return ModuleResult(
      moduleId: moduleId,
      totalScore: total,
      interpretation: interpretation,
      riskFlag: safetyReviewRequired,
      criteriaMet: false, // Criteria are unvalidated/unimplemented; never default positive.
      completedAt: DateTime.now(),
      itemScores: itemScores,
    );
  }
}

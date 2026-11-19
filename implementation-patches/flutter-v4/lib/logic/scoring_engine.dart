import "../models/assessment_models.dart";

/// Conservative interim engine for the unvalidated STN MVP.
///
/// This deliberately does NOT calculate a diagnostic score, apply generic
/// severity bands, or claim diagnostic criteria have been met. Until every
/// instrument and rule is traced to an approved source, the numeric total is
/// only a descriptive sum of entered response severities.
class ScoringEngine {
  static const _modulePrefixes = <String, String>{
    "MDD": "mdd_",
    "GAD": "gad_",
    "PTSD": "ptsd_",
    "ADHD": "adhd_",
  };

  ModuleResult score(
    String moduleId,
    List<Question> questions,
    List<Answer> answers,
  ) {
    final prefix = _modulePrefixes[moduleId];
    if (prefix == null || questions.isEmpty) {
      throw ArgumentError(
        'Unknown or unconfigured assessment module: $moduleId',
      );
    }
    if (questions.any((question) => !question.id.startsWith(prefix))) {
      throw ArgumentError('Question set does not belong to module: $moduleId');
    }

    final questionIds = questions.map((question) => question.id).toSet();
    if (questionIds.length != questions.length) {
      throw ArgumentError('Assessment module contains duplicate question IDs.');
    }

    final seen = <String>{};
    for (final answer in answers) {
      if (!questionIds.contains(answer.questionId)) {
        throw ArgumentError('Unknown question ID: ${answer.questionId}');
      }
      if (!seen.add(answer.questionId)) {
        throw ArgumentError(
          'Duplicate answer for question: ${answer.questionId}',
        );
      }
    }

    final itemScores = <String, int>{
      for (final answer in answers)
        answer.questionId: severityToScore(answer.severity),
    };
    final total = itemScores.values.fold<int>(0, (sum, value) => sum + value);
    final incomplete = questions.any((question) => !seen.contains(question.id));

    // Missing safety information is never interpreted as a negative answer.
    // Any non-zero response to a designated review item requires clinician
    // review. This is a conservative workflow flag, not a risk assessment.
    final safetyReviewRequired =
        incomplete ||
        questions.any((question) {
          if (!question.isRiskItem) return false;
          final answer = answers.where(
            (candidate) => candidate.questionId == question.id,
          );
          return answer.isEmpty || answer.first.severity != Severity.none;
        });

    final reviewText = safetyReviewRequired
        ? 'Clinician review required: the assessment is incomplete and/or a '
              'designated review item is positive or unanswered. This flag is '
              'not a risk assessment or crisis disposition. '
        : 'No review flag was triggered by this interim rule set; this is '
              'not proof of safety. ';
    const limitationText =
        'The response-severity sum is descriptive only, '
        'not a validated instrument score or diagnosis. Diagnostic criteria '
        'are not assessed.';

    return ModuleResult(
      moduleId: moduleId,
      totalScore: total,
      interpretation: '$reviewText$limitationText',
      riskFlag: safetyReviewRequired,
      criteriaMet: false,
      completedAt: DateTime.now(),
      itemScores: itemScores,
    );
  }
}

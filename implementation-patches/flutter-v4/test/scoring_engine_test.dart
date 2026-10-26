import 'package:flutter_test/flutter_test.dart';
import 'package:supportive_therapy_network/logic/scoring_engine.dart';
import 'package:supportive_therapy_network/models/assessment_models.dart';
import 'package:supportive_therapy_network/modules/mdd_module.dart';

void main() {
  group('ScoringEngine conservative prototype behaviour', () {
    final engine = ScoringEngine();

    test('does not claim diagnostic criteria are met', () {
      final answers = mddQuestions
          .map((q) => Answer(questionId: q.id, severity: Severity.extreme))
          .toList();
      final result = engine.score('MDD', mddQuestions, answers);
      expect(result.criteriaMet, isFalse);
      expect(result.interpretation, contains('not a validated instrument score'));
    });

    test('incomplete answers require clinician review', () {
      final result = engine.score('MDD', mddQuestions, [
        Answer(questionId: mddQuestions.first.id, severity: Severity.none),
      ]);
      expect(result.riskFlag, isTrue);
      expect(result.interpretation, contains('Clinician review required'));
    });

    test('positive designated review item requires clinician review', () {
      final answers = mddQuestions
          .map((q) => Answer(questionId: q.id,
              severity: q.id == 'mdd_q9_suicide' ? Severity.mild : Severity.none))
          .toList();
      final result = engine.score('MDD', mddQuestions, answers);
      expect(result.riskFlag, isTrue);
    });

    test('duplicate answer IDs are rejected', () {
      expect(() => engine.score('MDD', mddQuestions, [
        Answer(questionId: mddQuestions.first.id, severity: Severity.none),
        Answer(questionId: mddQuestions.first.id, severity: Severity.mild),
      ]), throwsArgumentError);
    });

    test('unknown question IDs are rejected', () {
      expect(() => engine.score('MDD', mddQuestions, [
        Answer(questionId: 'not-a-real-question', severity: Severity.none),
      ]), throwsArgumentError);
    });

    test('unknown modules are rejected', () {
      expect(() => engine.score('UNKNOWN', const <Question>[], const <Answer>[]),
          throwsArgumentError);
    });
  });
}

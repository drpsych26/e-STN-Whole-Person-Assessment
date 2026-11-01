import "package:flutter_test/flutter_test.dart";
import "package:supportive_therapy_network/screens/whole_person_initial_assessment_screen.dart";

void main() {
  group("STN paper-pilot core intake structure", () {
    test("contains exactly 25 unique Part A core items", () {
      expect(coreIntakeQuestions, hasLength(25));
      expect(coreIntakeQuestions.map((q) => q.number).toSet(), hasLength(25));
      expect(coreIntakeQuestions.first.number, 1);
      expect(coreIntakeQuestions.last.number, 25);
    });

    test("requires a synthetic case identifier", () {
      expect(CoreIntakeRules.isSyntheticCaseId("SYNTH-TEST-001"), isTrue);
      expect(CoreIntakeRules.isSyntheticCaseId("synth-demo-abc"), isTrue);
      expect(CoreIntakeRules.isSyntheticCaseId("CLIENT-001"), isFalse);
      expect(CoreIntakeRules.isSyntheticCaseId("NHI123456"), isFalse);
      expect(CoreIntakeRules.isSyntheticCaseId(""), isFalse);
    });

    test("does not treat missing safety-tagged answers as negative", () {
      final unresolved = CoreIntakeRules.unresolvedSafetyItems(const <int, int>{});
      expect(unresolved, [14, 19, 20, 21, 22, 23, 24]);
    });

    test("flags endorsed safety-tagged items for human review", () {
      final answers = {for (var i = 1; i <= 25; i++) i: 0};
      answers[20] = 2;
      expect(CoreIntakeRules.unresolvedSafetyItems(answers), [20]);
    });

    test("a zero response does not trigger an interim review flag", () {
      final answers = {for (var i = 1; i <= 25; i++) i: 0};
      expect(CoreIntakeRules.unresolvedSafetyItems(answers), isEmpty);
      expect(CoreIntakeRules.isComplete(answers), isTrue);
    });

    test("incomplete core responses remain incomplete", () {
      final answers = {for (var i = 1; i < 25; i++) i: 0};
      expect(CoreIntakeRules.isComplete(answers), isFalse);
      expect(CoreIntakeRules.answeredCount(answers), 24);
    });
  });
}

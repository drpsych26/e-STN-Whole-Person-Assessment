import "package:flutter_test/flutter_test.dart";
import "package:supportive_therapy_network/models/core_intake.dart";

void main() {
  group("STN paper-pilot core intake structure", () {
    test("contains exactly 25 unique Part A core items", () {
      expect(coreIntakeQuestions, hasLength(25));
      expect(coreIntakeQuestions.map((q) => q.number).toSet(), hasLength(25));
      expect(coreIntakeQuestions.first.number, 1);
      expect(coreIntakeQuestions.last.number, 25);
    });

    test("preserves all 25 Part A source item wordings", () {
      const expected = <String>[
        "Low, depressed, empty or hopeless mood.",
        "Much less interest or pleasure in usual activities.",
        "Marked fatigue or unusually low energy.",
        "Sleep problems that interfere with daytime functioning.",
        "Excessive worry, tension or feeling on edge.",
        "Sudden episodes of intense fear with strong physical symptoms.",
        "Distressing memories, nightmares, avoidance or hyper-alertness after frightening events.",
        "Intrusive unwanted thoughts or urges that are hard to dismiss.",
        "Repeated behaviours or mental rituals done to reduce distress.",
        "Periods of unusually high energy, reduced need for sleep, racing thoughts or increased activity.",
        "Impulsive or risky behaviour that has caused meaningful problems.",
        "Persistent problems with attention, organisation or completing tasks.",
        "Long-standing social-communication or sensory differences affecting daily life.",
        "Hearing, seeing or strongly believing things others do not that cause distress or impairment.",
        "Feeling unreal, detached from yourself, or losing time/memory unexpectedly.",
        "Alcohol use has caused concern, loss of control or consequences.",
        "Drug or non-prescribed medication use has caused concern, loss of control or consequences.",
        "Eating, weight or body-image concerns are affecting health or daily life.",
        "Anger, aggression or loss of control has frightened you or others.",
        "Thoughts of self-harm, suicide, or wishing you were dead.",
        "Current intention, plan, preparation or access to means for suicide.",
        "Thoughts, intention, plan or preparation to seriously harm another person.",
        "You currently feel unsafe because of violence, abuse, exploitation, stalking or coercive control.",
        "Housing, food, power, transport or other basic needs are unstable enough to affect health or safety.",
        "Emotional or behavioural difficulties are significantly affecting work, study, parenting, relationships or self-care.",
      ];
      expect(coreIntakeQuestions.map((question) => question.text).toList(), expected);
    });

    test("requires a synthetic case identifier", () {
      expect(CoreIntakeRules.isSyntheticCaseId("SYNTH-TEST-001"), isTrue);
      expect(CoreIntakeRules.isSyntheticCaseId("synth-demo-abc"), isTrue);
      expect(CoreIntakeRules.isSyntheticCaseId("CLIENT-001"), isFalse);
      expect(CoreIntakeRules.isSyntheticCaseId("NHI123456"), isFalse);
      expect(CoreIntakeRules.isSyntheticCaseId(""), isFalse);
    });

    test("requires a synthetic tester alias", () {
      expect(CoreIntakeRules.isSyntheticTesterAlias("TESTER-01"), isTrue);
      expect(CoreIntakeRules.isSyntheticTesterAlias("TESTER-UAT-02"), isTrue);
      expect(CoreIntakeRules.isSyntheticTesterAlias("Real Person"), isFalse);
      expect(CoreIntakeRules.isSyntheticTesterAlias(""), isFalse);
    });

    test("does not treat missing safety-tagged answers as negative", () {
      expect(CoreIntakeRules.unresolvedSafetyItems(const <int, int>{}),
          [14, 19, 20, 21, 22, 23, 24]);
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

    test("rejects response values outside the defined 0–4 scale", () {
      for (final invalid in [-1, 5, 99]) {
        final answers = {for (var i = 1; i <= 25; i++) i: 0};
        answers[1] = invalid;
        expect(CoreIntakeRules.areAnswersValid(answers), isFalse);
        expect(CoreIntakeRules.isComplete(answers), isFalse);
        expect(CoreIntakeRules.answeredCount(answers), 24);
      }
    });

    test("rejects unknown question identifiers", () {
      final answers = {for (var i = 1; i <= 25; i++) i: 0, 26: 0};
      expect(CoreIntakeRules.areAnswersValid(answers), isFalse);
      expect(CoreIntakeRules.isComplete(answers), isFalse);
      expect(CoreIntakeRules.answeredCount(answers), 25);
    });

    test("invalid or missing safety values remain unresolved", () {
      final answers = {for (var i = 1; i <= 25; i++) i: 0};
      answers[20] = 7;
      answers.remove(21);
      expect(CoreIntakeRules.unresolvedSafetyItems(answers), [20, 21]);
    });
  });
}

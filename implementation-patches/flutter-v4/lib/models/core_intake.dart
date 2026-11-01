class CoreIntakeQuestion {
  final int number;
  final String text;
  final bool safetyTagged;
  const CoreIntakeQuestion({required this.number, required this.text, this.safetyTagged = false});
}

const coreIntakeQuestions = <CoreIntakeQuestion>[
  CoreIntakeQuestion(number: 1, text: "Low, depressed, empty or hopeless mood."),
  CoreIntakeQuestion(number: 2, text: "Much less interest or pleasure in usual activities."),
  CoreIntakeQuestion(number: 3, text: "Marked fatigue or unusually low energy."),
  CoreIntakeQuestion(number: 4, text: "Sleep problems that interfere with daytime functioning."),
  CoreIntakeQuestion(number: 5, text: "Excessive worry, tension or feeling on edge."),
  CoreIntakeQuestion(number: 6, text: "Sudden episodes of intense fear with strong physical symptoms."),
  CoreIntakeQuestion(number: 7, text: "Distressing memories, nightmares, avoidance or hyper-alertness after frightening events."),
  CoreIntakeQuestion(number: 8, text: "Intrusive unwanted thoughts or urges that are hard to dismiss."),
  CoreIntakeQuestion(number: 9, text: "Repeated behaviours or mental rituals done to reduce distress."),
  CoreIntakeQuestion(number: 10, text: "Periods of unusually high energy, reduced need for sleep, racing thoughts or increased activity."),
  CoreIntakeQuestion(number: 11, text: "Impulsive or risky behaviour that has caused meaningful problems."),
  CoreIntakeQuestion(number: 12, text: "Persistent problems with attention, organisation or completing tasks."),
  CoreIntakeQuestion(number: 13, text: "Long-standing social-communication or sensory differences affecting daily life."),
  CoreIntakeQuestion(number: 14, text: "Hearing, seeing or strongly believing things others do not that cause distress or impairment.", safetyTagged: true),
  CoreIntakeQuestion(number: 15, text: "Feeling unreal, detached from yourself, or losing time/memory unexpectedly."),
  CoreIntakeQuestion(number: 16, text: "Alcohol use has caused concern, loss of control or consequences."),
  CoreIntakeQuestion(number: 17, text: "Drug or non-prescribed medication use has caused concern, loss of control or consequences."),
  CoreIntakeQuestion(number: 18, text: "Eating, weight or body-image concerns are affecting health or daily life."),
  CoreIntakeQuestion(number: 19, text: "Anger, aggression or loss of control has frightened you or others.", safetyTagged: true),
  CoreIntakeQuestion(number: 20, text: "Thoughts of self-harm, suicide, or wishing you were dead.", safetyTagged: true),
  CoreIntakeQuestion(number: 21, text: "Current intention, plan, preparation or access to means for suicide.", safetyTagged: true),
  CoreIntakeQuestion(number: 22, text: "Thoughts, intention, plan or preparation to seriously harm another person.", safetyTagged: true),
  CoreIntakeQuestion(number: 23, text: "You currently feel unsafe because of violence, abuse, exploitation, stalking or coercive control.", safetyTagged: true),
  CoreIntakeQuestion(number: 24, text: "Housing, food, power, transport or other basic needs are unstable enough to affect health or safety.", safetyTagged: true),
  CoreIntakeQuestion(number: 25, text: "Emotional or behavioural difficulties are significantly affecting work, study, parenting, relationships or self-care."),
];

const coreIntakeResponseLabels = <String>[
  "Not at all / no",
  "A little / occasionally",
  "Moderately / sometimes",
  "A lot / often",
  "Extreme / nearly always",
];

class CoreIntakeRules {
  static const safetyItemNumbers = <int>{14, 19, 20, 21, 22, 23, 24};

  static bool isSyntheticCaseId(String value) => RegExp(
        r"^SYNTH-[A-Z0-9][A-Z0-9-]{2,39}$",
        caseSensitive: false,
      ).hasMatch(value.trim());

  static bool isSyntheticTesterAlias(String value) => RegExp(
        r"^TESTER-[A-Z0-9][A-Z0-9-]{1,30}$",
        caseSensitive: false,
      ).hasMatch(value.trim());

  static bool isComplete(Map<int, int> answers) =>
      coreIntakeQuestions.every((question) => answers.containsKey(question.number));

  static int answeredCount(Map<int, int> answers) =>
      coreIntakeQuestions.where((question) => answers.containsKey(question.number)).length;

  static List<int> unresolvedSafetyItems(Map<int, int> answers) =>
      safetyItemNumbers.where((number) => answers[number] == null || answers[number]! > 0).toList()..sort();
}

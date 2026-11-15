import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:supportive_therapy_network/main.dart';
import 'package:supportive_therapy_network/screens/profiles_screen.dart';
import 'package:supportive_therapy_network/screens/whole_person_initial_assessment_screen.dart';

void main() {
  testWidgets('STN app opens the assessment dashboard', (tester) async {
    await tester.pumpWidget(const STNApp());

    expect(find.text('STN Whole Person Assessment — Flutter MVP'), findsOneWidget);
    expect(find.text('Depression symptom review'), findsOneWidget);
    expect(find.text('Anxiety symptom review'), findsOneWidget);
    expect(find.text('Trauma symptom review'), findsOneWidget);
    expect(find.text('Attention and impulsivity review'), findsOneWidget);
  });

  testWidgets('MDD module opens and displays its questions', (tester) async {
    await tester.pumpWidget(const STNApp());
    await tester.tap(find.text('Depression symptom review'));
    await tester.pumpAndSettle();

    expect(find.text('Depressed mood most of the day, nearly every day.'),
        findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Save synthetic response summary'),
      300,
      scrollable: find.byType(Scrollable).last,
    );
    await tester.pumpAndSettle();
    expect(find.text('Save synthetic response summary'), findsOneWidget);
  });

  testWidgets('profile screen accepts synthetic identifiers only and exposes no patient PII fields',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: ProfilesScreen()),
    );

    expect(find.text('Synthetic case ID'), findsOneWidget);
    expect(find.text('Synthetic tester alias'), findsOneWidget);
    expect(find.text('Client full name'), findsNothing);
    expect(find.text('DOB (YYYY-MM-DD)'), findsNothing);
    expect(find.text('Contact (phone/email)'), findsNothing);
    expect(find.text('Registration number'), findsNothing);
  });

  testWidgets('storage initialisation failure disables assessment access',
      (tester) async {
    await tester.pumpWidget(
      const STNApp(startupError: 'secure storage unavailable'),
    );
    expect(find.text('STN cannot start safely'), findsOneWidget);
    expect(find.textContaining('assessment has been disabled'), findsOneWidget);
  });

  testWidgets('Whole Person intake renders all 25 items and synthetic-only boundary',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: WholePersonInitialAssessmentScreen()),
    );
    await tester.pumpAndSettle();

    expect(find.text('Whole Person Initial Assessment'), findsOneWidget);
    expect(find.textContaining('SYNTHETIC DATA ONLY'), findsOneWidget);
    expect(find.text('Progress: 0 / 25 answered'), findsOneWidget);

    for (var item = 1; item <= 25; item++) {
      final card = find.byKey(ValueKey('core-item-$item'));
      await tester.scrollUntilVisible(
        card,
        300,
        scrollable: find.byType(Scrollable).last,
      );
      await tester.pumpAndSettle();
      expect(card, findsOneWidget);
    }

    await tester.scrollUntilVisible(
      find.text('Save draft'),
      300,
      scrollable: find.byType(Scrollable).last,
    );
    await tester.pumpAndSettle();
    expect(find.text('Save draft'), findsOneWidget);
    expect(find.text('Complete simulation'), findsOneWidget);
  });

  testWidgets('Whole Person intake updates progress when an answer is selected',
      (tester) async {
    await tester.pumpWidget(
      const MaterialApp(home: WholePersonInitialAssessmentScreen()),
    );
    await tester.pumpAndSettle();

    final firstItem = find.byKey(const ValueKey('core-item-1'));
    await tester.scrollUntilVisible(
      firstItem,
      300,
      scrollable: find.byType(Scrollable).last,
    );
    await tester.pumpAndSettle();

    final zeroResponse = find.descendant(
      of: firstItem,
      matching: find.widgetWithText(ChoiceChip, '0'),
    );
    await tester.tap(zeroResponse);
    await tester.pumpAndSettle();

    expect(find.textContaining('Progress: 1 / 25 answered'), findsOneWidget);
  });
}

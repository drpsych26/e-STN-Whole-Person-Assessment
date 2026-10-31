import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import '../lib/main.dart';

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
      find.text('Save response summary'),
      300,
      scrollable: find.byType(Scrollable).last,
    );
    await tester.pumpAndSettle();
    expect(find.text('Save response summary'), findsOneWidget);
  });

  testWidgets('storage initialisation failure disables assessment access',
      (tester) async {
    await tester.pumpWidget(
      const STNApp(startupError: 'secure storage unavailable'),
    );
    expect(find.text('STN cannot start safely'), findsOneWidget);
    expect(find.textContaining('assessment has been disabled'), findsOneWidget);
  });
}

import 'package:flutter_test/flutter_test.dart';
import 'package:supportive_therapy_network/main.dart';

void main() {
  testWidgets('STN app opens the assessment dashboard', (tester) async {
    await tester.pumpWidget(const STNApp());

    expect(find.text('STN Diagnostic Tool'), findsOneWidget);
    expect(find.text('Major Depressive Disorder (DSM gating)'), findsOneWidget);
    expect(find.text('Generalised Anxiety Disorder'), findsOneWidget);
    expect(find.text('PTSD / Trauma'), findsOneWidget);
    expect(find.text('ADHD'), findsOneWidget);
  });

  testWidgets('MDD module opens and displays its questions', (tester) async {
    await tester.pumpWidget(const STNApp());
    await tester.tap(find.text('Major Depressive Disorder (DSM gating)'));
    await tester.pumpAndSettle();

    expect(find.text('Depressed mood most of the day, nearly every day.'),
        findsOneWidget);
    expect(find.text('Score + Save (Encrypted)'), findsOneWidget);
  });
}

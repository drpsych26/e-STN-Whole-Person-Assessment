import "package:flutter/material.dart";
import "package:hive_flutter/hive_flutter.dart";

import "screens/home_screen.dart";
import "storage/secure_hive.dart";

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();

  Object? startupError;
  try {
    await Hive.initFlutter();
    await SecureHive.initEncryptedBoxes();
  } catch (error) {
    startupError = error;
  }

  runApp(STNApp(startupError: startupError));
}

// STN brand: near-black canvas, brand purple accent (#AF2CFF), white text.
// Source: docs/brand/STN-BRAND-AND-ASSET-CONTROL.md. Logo is never recoloured.
ThemeData _stnTheme() {
  const purple = Color(0xFFAF2CFF);
  const canvas = Color(0xFF08070A);
  const panel = Color(0xFF14121B);
  final scheme = ColorScheme.fromSeed(
    seedColor: purple,
    brightness: Brightness.dark,
  ).copyWith(
    primary: purple,
    onPrimary: Colors.black,
    surface: panel,
    onSurface: const Color(0xFFF7F4FA),
  );
  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: canvas,
    appBarTheme: const AppBarTheme(backgroundColor: canvas, foregroundColor: Color(0xFFF7F4FA), elevation: 0),
  );
}

class STNApp extends StatelessWidget {
  final Object? startupError;

  const STNApp({super.key, this.startupError});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: "Supportive Therapy Network",
      theme: _stnTheme(),
      home: startupError == null
          ? const HomeScreen()
          : StartupFailureScreen(error: startupError!),
    );
  }
}

class StartupFailureScreen extends StatelessWidget {
  final Object error;

  const StartupFailureScreen({super.key, required this.error});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("STN cannot start safely")),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Icon(Icons.error_outline, size: 40, color: Colors.red),
            const SizedBox(height: 16),
            const Text(
              "Secure local storage could not be initialised. "
              "The assessment has been disabled to prevent unsaved or "
              "unprotected records.",
            ),
            const SizedBox(height: 12),
            SelectableText(error.toString()),
            const SizedBox(height: 12),
            const Text(
              "Do not enter client information. Close the app and contact "
              "the system administrator.",
            ),
          ],
        ),
      ),
    );
  }
}

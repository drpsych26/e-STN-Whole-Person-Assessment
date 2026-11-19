import "package:flutter/material.dart";
import "package:hive_flutter/hive_flutter.dart";
import "screens/home_screen.dart";
import "storage/secure_hive.dart";

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Hive.initFlutter();
  await SecureHive.initEncryptedBoxes();
  runApp(const STNApp());
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
  const STNApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: "Supportive Therapy Network",
      theme: _stnTheme(),
      home: const HomeScreen(),
    );
  }
}

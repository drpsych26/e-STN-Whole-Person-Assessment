# Brand changes for the Flutter v4 app

- `lib/main.dart`: dark brand theme (canvas #08070A, purple #AF2CFF, white text).
- `lib/screens/home_screen.dart`: canonical logo `assets/brand/stn-logo-original.png` in the app bar.
- Required in the app's `pubspec.yaml` (the maintained repo copy has no pubspec; see STN-H08):

```yaml
flutter:
  uses-material-design: true
  assets:
    - assets/brand/stn-logo-original.png
```

Copy `assets/brand/stn-logo-original.png` (sha256 93beeea1…) into the app's `assets/brand/` folder. Do not re-encode or recolour it.

Fonts: the app uses the platform default. Manrope and Source Serif 4 are not bundled; bundling them is a build task that needs the font files and their licence confirmed.

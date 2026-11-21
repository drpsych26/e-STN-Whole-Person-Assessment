# STN Android identity, launcher icon and release signing

Copied over the `android/` folder that `flutter create --platforms=android` generates
(pinned Flutter 3.47.9) by the **STN Android APK build** workflow.

| Item | Value |
|---|---|
| Application ID / namespace | `network.supportivetherapy.app` (from supportivetherapy.network) |
| Launcher label | `STN` |
| Launcher icon | STN head-and-brain mark, `#AF2CFF` on white; adaptive + themed (monochrome) icon. 512 px master: `assets/brand/stn-app-icon-512.png` |
| Release signing | STN upload key, alias `stn-upload`, PKCS12, RSA 4096, valid to 2054 |
| Signing certificate SHA-256 | `6c5b57ada0570b2a34c83711e527ca673d09534e481be0adb62e01c3342d6bb7` |

## Signing

`app/build.gradle.kts` signs release builds from `android/key.properties`. If that file is
absent, the release APK is left **unsigned**; it never falls back to the debug key.

The keystore and its password are **never committed** (this repository is public). CI reads
them from repository secrets:

- `STN_ANDROID_KEYSTORE_BASE64`: the `.p12` file, base64-encoded on one line
- `STN_ANDROID_KEYSTORE_PASSWORD`: the store/key password (same value)

The workflow refuses to build if either secret is missing, and fails if the APK is not signed
by the certificate above or does not carry the expected application ID.

Every future update must be signed with this same key, or Android will refuse it as an update.
When publishing to Google Play, enrol in Play App Signing and register this as the upload key.

# Android release signing — secure local setup

**This repository does not contain a keystore, private key, password, alias value, or production signing configuration.** Debug builds deliberately require none of them.

Use this procedure only on the owner's controlled Kali Linux workstation after the normal engineering and release gates are satisfied. Do not paste any secret into chat, GitHub, a ticket, an issue, a log, shell history, or a tracked file.

## Versioned safe assets

- [key.properties.example](key.properties.example) lists the **property names only**.
- The root `.gitignore` excludes `*.jks`, `*.keystore`, and `key.properties`.
- The debug CI workflow continues to build `app-debug.apk`; it must never use release material.

## Local owner procedure (Kali Linux)

1. Install the required JDK and Flutter toolchain locally. Confirm `keytool -help` works.
2. Create or obtain the release keystore **locally**, outside this repository. Keep its absolute path and credentials private.
3. In the generated Flutter app's `android/` folder, copy `key.properties.example` to `key.properties`.
4. Fill only these four fields locally:

   ```properties
   storeFile=/absolute/path/outside/the/repository/stn-release.jks
   storePassword=<local secret>
   keyAlias=<local alias>
   keyPassword=<local secret>
   ```

5. Add the Kotlin DSL release-signing block below to that app's `android/app/build.gradle.kts`. This block configures a release signing config only when the untracked file exists, and makes the release packaging task fail instead of silently falling back to debug signing.

   ```kotlin
   import java.io.FileInputStream
   import java.util.Properties

   val stnKeystoreProperties = Properties()
   val stnKeystorePropertiesFile = rootProject.file("key.properties")
   if (stnKeystorePropertiesFile.exists()) {
       stnKeystoreProperties.load(FileInputStream(stnKeystorePropertiesFile))
   }

   // Place inside android { ... }:
   if (stnKeystorePropertiesFile.exists()) {
       signingConfigs {
           create("release") {
               keyAlias = stnKeystoreProperties["keyAlias"] as String
               keyPassword = stnKeystoreProperties["keyPassword"] as String
               storeFile = file(stnKeystoreProperties["storeFile"] as String)
               storePassword = stnKeystoreProperties["storePassword"] as String
           }
       }
   }

   buildTypes {
       getByName("release") {
           signingConfigs.findByName("release")?.let { signingConfig = it }
       }
   }

   tasks.matching { task ->
       task.name.startsWith("package") && task.name.contains("Release")
   }.configureEach {
       doFirst {
           check(signingConfigs.findByName("release") != null) {
               "Release signing is not configured. Create untracked android/key.properties locally."
           }
       }
   }
   ```

6. Build a **local** release candidate only after confirming the local configuration with the app's Gradle/Flutter version:

   ```bash
   flutter build apk --release
   ```

7. Verify the generated APK's signing certificate and record only the artifact SHA-256 and non-secret certificate fingerprint in a private release record. Do not upload the keystore or `key.properties`.

## Important limitations

- This setup is intentionally not active in GitHub Actions and produces no signed artifact in this repository.
- A successfully signed APK is engineering evidence only. It is not clinical approval, privacy approval, a production deployment, or authorization to process real-client data.
- Before any release build can leave private testing, the exact release gates in `docs/release/INVESTOR-READINESS-AND-CONTROLLED-RELEASE-PLAN-2026-11-04.md` must be closed and documented.

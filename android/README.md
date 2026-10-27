# Zoom2Youtube – Android app

Native Android client (Kotlin + Jetpack Compose) for the Zoom2Youtube web server.
The backend is unchanged: the app signs in with the same admin username/password as the
web UI and calls the existing `/api/*` endpoints.

## Flow

1. **Sign in** – server URL (default `https://z2y.neemanet.com`), username, password.
   The password is stored encrypted (Android Keystore) so the app can silently re-login when the
   server's 24h session expires.
2. **Recordings** – pick 1/5/7/30 days, tap a recording, **Download & continue**
   (the server downloads it from Zoom).
3. **Upload** – choose מסכת + דף; title (`מסכת | דף | בית כנסת נריה`) and thumbnail text
   (`מסכת - דף`) are generated exactly like the web UI. Pick privacy and playlist, optionally
   preview the thumbnail, then **Upload to YouTube**. On success: Open / Share / Copy link.

## Build

Requires Android Studio (Ladybug or newer) with JDK 17 and Android SDK 35.

1. `File > Open…` and select this `android/` folder; let Gradle sync.
   (If Studio asks to upgrade AGP/Gradle, accepting is fine.)
2. Run on a device/emulator, or build an APK: `Build > Build APK(s)`.

Command line, after Studio has created `local.properties` (or `ANDROID_HOME` is set):

```bash
gradle wrapper --gradle-version 8.9   # one-time; generates ./gradlew
./gradlew assembleDebug               # app/build/outputs/apk/debug/app-debug.apk
```

Debug builds allow plain `http://` so you can test against a local server
(`http://10.0.2.2:5000` from the emulator). Release builds require HTTPS.

## Behaviour worth knowing

- **Uploads survive proxy timeouts.** `/api/upload` blocks until YouTube has the video, and a
  proxy such as Cloudflare cuts requests at ~100s. The server de-duplicates by `video_file`, so
  the app re-asks every few seconds (up to 2h) and picks up the result. The server keeps
  uploading even if the phone loses connection.
- **Downloads are not auto-retried.** The server writes the MP4 in place, so a retry after a
  dropped connection could treat a half-written file as already downloaded. On a dropped
  connection the app tells you to check it finished before uploading.
- **Google sign-in** (needs `AUTH_MODE=google` or `both` on the server): the app opens `/auth/google?app=1` in a Chrome
  Custom Tab; after sign-in the server redirects to `z2y://login?code=<one-time code>` and the app swaps the code for a
  session cookie via `POST /auth/app-exchange`. There is no stored password in this mode, so when the 24h session
  lapses you sign in with Google again. Requires the server version that includes `/auth/app-exchange`.
- Server-side `SESSION_COOKIE_SECURE=true` needs an `https://` server URL.

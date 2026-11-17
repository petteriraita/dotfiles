# Local API setup and evidence

## Implemented contacts

`google_contacts.py` uses the existing installed-app OAuth client at `/home/pt/dev/personal/automation/calendar-llm/credentials.json`. It stores a separate refresh credential in `~/.config/phone-schedule/google-contacts-token.json` (600, directory 700). Google People API was enabled in that project. On 2026-11-04:

- Google account identity and People API access were verified.
- Automatic credential refresh was exercised successfully without another browser interaction.
- `UHCSR Insurance - UIUC Account Support`, `+18882244883`, was created and read back as `people/c1060869420620688874`.
- Repeating ensure-contact returned the same contact with `created=false`.
- Physical phone sync was not independently verified.

OAuth consent can still be revoked. The project's OAuth publishing status is not verified here; Google Testing-mode grants involving Contacts may expire after seven days. Check Google Auth Platform → Audience before promising a never-reauthorize setup. Do not ask for repeated debugging codes to fix a cloud authorization issue.

## Clock source/build

The user rejected proprietary/ad-supported alarm apps. This is a **modified local Fossify build**, not a stock supported Fossify API and not a new alarm engine from scratch.

- Upstream: https://github.com/FossifyOrg/Clock
- Pin: `4ecb9e33c51c0b2096af2379e7ac9dc17c3e07e6` (1.6.0).
- License: GPL-3.0-or-later; included under `assets/fossify-api/LICENSE`.
- Package: `org.fossify.clock.schedule`; app label: `Clock Local API`.
- Source additions: `assets/fossify-api/ScheduleProvider.kt`, `ScheduleClient.java`.
- Recipe: `python3 scripts/build_clock_api.py --sdk PATH_TO_ANDROID_SDK`.
- Default existing SDK: `/home/pt/dev/personal/apps/android-alarm-helper/tools`; needs platform 36 and build-tools 36.0.0. Build also needs JDK 21, Git, zip/unzip, and network access for the pinned upstream/Gradle dependencies. JDK and zip are declared in the workstation package manifest.
- SDK acquisition is not automated by install.sh. Existing archives came from `https://dl.google.com/android/repository/platform-36_r02.zip` and `https://dl.google.com/android/repository/build-tools_r36_linux.zip`. Restore/accept the SDK separately and pass its location; do not claim a skill symlink restores it.
- Generated source/cache: `~/.cache/phone-schedule/fossify-clock-source`.
- APK: `~/.cache/phone-schedule/fossify-clock-local-api.apk`.
- Client: `~/.cache/phone-schedule/schedule-client.jar`.
- Current signing key is the user's Android debug keystore, `~/.android/debug.keystore`; preserve it privately for compatible updates. This is a local debug build, not a published/hardened upstream release. No key material is stored in dotfiles.

The recipe inserts an exported ContentProvider but rejects calls from any UID whose installed packages do not include `com.termux` (and allows the host app itself). It adds package visibility for Termux. The provider runs the actual operation after clearing Binder caller identity. There is no HTTP server, bearer token in command arguments, or Internet permission.

Provider operations: check, list, get, idempotent create, cancel API-owned alarm. New alarms are one-shot, silent, vibrating, and limited to today/tomorrow. Native AlarmManager registration errors propagate; stored records are read back. Original Fossify boot/time-change scheduling is adjusted to retain API alarms' absolute trigger times. Receiver/vibration-request timestamps are recorded for delivery diagnostics. Those timestamps are not proof of physical vibration.

## Phone deployment

1. Transfer the generated APK to `~/storage/downloads/Clock-Local-API.apk` using existing SSH/scp. Do not navigate the phone UI.
2. The user manually installs it, opens it once and grants notifications/exact-alarm access as needed. It does not replace Google Clock or import/change its alarms.
3. Stage the client jar at `~/.local/share/phone-schedule/schedule-client.jar` on the phone. Set mode 400: Android 14+ rejects writable dynamically loaded dex.
4. Use `scripts/clock_api.py check`, then list/create/get/cancel. The helper uses SSH and an app-level ContentResolver client. The privileged `content` shell executable is not used.

The native client bootstraps an Android app Context with ActivityThread/ContextImpl. This part uses internal framework interfaces and is Android-version-sensitive; context identity was verified on this Android 16 phone. An OS upgrade may require updating/retesting the client. Report that compatibility issue directly; do not silently fall back to screen automation or repeated ADB pairing.

## Verified versus pending (2026-11-04)

Verified:
- Pinned modified Fossify source compiled successfully.
- APK signing verification passed; certificate SHA-256 `669bec4cdf23a0c7b17e6921dd280b969ae65151b33b8049e777a03928dedfaa`.
- APK manifest has no Internet permission.
- Phone APK copy hash matched local SHA-256 `a0b96445ac1c7ef9a2a698050cb9e52b776ffd0c5c2b5f277a41ec35315071de`.
- CLI client runs under UID 10245 with package and operation package both `com.termux`.

Pending:
- User APK installation and required Android permission grants.
- End-to-end provider access and an untrusted-caller rejection test where feasible.
- Silent/vibrating alarm create/readback, idempotency and cancellation on device.
- Actual timed delivery and user confirmation of physical vibration.
- Reboot/offline recovery test; do not claim those have passed merely because upstream supports boot rescheduling.
- The real UHCSR call alarm; choose a fresh future time after setup and calendar checks.

Daily prerequisites after verified installation: phone connectivity/Tailscale + Termux sshd/key + app permissions/client. No ADB pairing or connection port is part of the daily alarm workflow. Stored alarms fire locally while laptop/Tailscale is disconnected, subject to Android/device state. Force-stop, revoked permissions, device shutdown and vendor restrictions remain relevant.

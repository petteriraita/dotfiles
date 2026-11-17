---
name: schedule
description: Create and verify Google-account contacts and silent vibrating action alarms through CLI/APIs. Use for phone alarms or call reminders; use calendar-planning for broader daily or weekly plans.
---

# Schedule

The user requires **CLI/API only**: no phone taps, swipes, screen navigation or UI automation. Default alarms are silent, vibration on, with explicit action labels. Save contacts to `petteri.r.raita@gmail.com`, never SIM/device, using searchable organization + purpose names. Do not require a proprietary/ad-supported app. Do not silently substitute notifications for native alarms.

Existing Google Clock alarms remain in Google Clock. Its standard alarm intent cannot return saved alarm records for verification. For AI-managed alarms, the user authorized an API-capable alternative; the prepared solution is a local, GPL Fossify Clock build called **Clock Local API**, package `org.fossify.clock.schedule`. It preserves Fossify's alarm engine and adds an API restricted to the installed Termux UID. No network listener or Internet permission. Do not call this the stock Fossify app, claim it changes Google Clock's private database, or claim reliability from compilation alone.

## Contacts — Google People API

```sh
python3 scripts/google_contacts.py status
python3 scripts/google_contacts.py ensure-contact --name 'UHCSR Insurance - UIUC Account Support' --number '+18882244883' --notes 'Account support; Mon-Fri 7am-7pm Central.'
```

The helper verifies the Google identity, checks existing phone numbers, creates only if absent, then GETs the returned record to verify name/number. A matching number under a different name is preserved and reported for inspection. Cloud readback does not prove completed phone sync.

Authorization is configured and automatic refresh was verified on 2026-11-04. It uses:
- Client: `/home/pt/dev/personal/automation/calendar-llm/credentials.json` (relocated from the obsolete `/home/pt/dev/calendar-llm` path).
- Separate private token: `/home/pt/.config/phone-schedule/google-contacts-token.json`, parent mode 700, file mode 600. Never print tokens or put credentials in dotfiles.
- Google People API is enabled in the existing project. Google Tasks credentials/scopes are separate and were not modified.

If Google genuinely requires fresh authorization, `python3 scripts/google_contacts.py auth` opens a normal laptop-browser consent flow with state and PKCE. The user must grant **Contacts**, not just email identity. Do not request passwords/MFA codes. `status --refresh` exercises automatic refresh when troubleshooting, not on every action. If the OAuth project remains in Testing, Contacts refresh grants may expire after seven days; check publishing status before promising unattended long-term access. Revocation/reinstallation can still require exceptional reauthorization.

## Alarms — native local API

```sh
python3 scripts/clock_api.py check
python3 scripts/clock_api.py list
python3 scripts/clock_api.py create --at '2026-11-04T13:00:00-06:00' --label 'Call UHCSR +1 888-224-4883: fix registration Error 10002'
python3 scripts/clock_api.py get --id ID
python3 scripts/clock_api.py cancel --id ID
```

Replace examples with the actual future date/time. The current API supports one-time alarms **today or tomorrow in the phone's timezone**; do not pretend it supports arbitrary later dates. It preserves the absolute trigger time for reboot/time-change recovery. Create is idempotent for the same label/time and returns an ID; the laptop helper GETs that ID and verifies enabled, one-shot, silent, vibration and trigger time. Cancellation is restricted to API-created alarms. Do not modify unrelated alarms.

For calls, verify number/hours, use the phone's actual time/timezone, check calendar conflicts and allow time before closing/next commitment. Use action labels, not `Reminder`; avoid sensitive IDs on the lock screen. A successful native registration plus readback proves stored settings, not physical vibration. Initial deployment needs a short silent firing test: check receiver/vibration-invocation timestamps, stop the test, and ask the user to confirm actual vibration. Reboot recovery also needs a real device test before claiming it was verified.

### Connection and installation

Use the existing SSH setup in `../android-phone-ssh/SKILL.md`. Daily alarm operations need phone connectivity/Tailscale, Termux sshd/key, the installed Clock Local API app, and the staged native client. They need **no ADB connection or pairing codes**. The client uses an app-level ContentResolver under the Termux UID; the privileged Android `content` shell CLI is not a substitute. Google Contacts commands need Google API connectivity, not the phone or Tailscale.

If a phone command fails, tell the user immediately and stop dependent writes. Follow the Android phone skill for a targeted diagnostic; do not loop, scan ports, or ask for a new pairing code. A timeout after a write has unknown outcome: inspect by ID/idempotency key before retrying. Continue independent tasks while blocked.

The native app needs notifications and native exact-alarm permission. One-time manual installation/permission grants are Android setup requirements; the agent must not drive the screen. After an alarm is stored, firing is local and does not need the laptop/Tailscale connected. Android force-stop, revoked permissions, vendor background restrictions, and device shutdown are material limitations.

Build/deploy source and current device verification status: [references/local-api-setup.md](references/local-api-setup.md). Legacy `phone_schedule.py` only tests/requests the older native intent path; its contact editor is disabled. Prefer the actual API helpers above.

## Restoration and reporting

Canonical folder: `/home/pt/dev/config/dotfiles/codex-skills/schedule/`; `install.sh --only links` restores discovery. App source additions and the pinned build recipe are here; SDK/build tools, signing key, Google OAuth credentials/token, SSH key/config, phone APK/client installation and permissions need separate restoration. Never claim linking the skill restores those runtime prerequisites. Update the Obsidian skill catalog and explicitly notify the user when its description is saved there.

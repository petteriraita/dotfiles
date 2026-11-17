# Historical Android CLI findings

This reference records explored options, not the current workflow. Use `local-api-setup.md` for the implemented local API and the main skill for Google Contacts.

The user requires CLI/API-only operation and rejected proprietary/ad-supported app requirements. Sleep as Android was investigated for its API but is **not** the selected solution. No agent phone UI automation is permitted.

## Android access

SSH reaches Termux's app UID, not ADB shell. This phone rejected Termux `content` queries/insertion with ACCESS_CONTENT_PROVIDERS_EXTERNALLY. ADB pairing succeeded and reached UID 2000, allowing Contacts Provider queries. Google Clock's seven alarms were observed before the user prohibited UI navigation; that screen-driven technique must not be reused.

ADB identity lives under `~/.android/adbkey*`; do not delete it or request fresh pairing on every disconnect. Reuse existing authorization. Connection ports may change, and wireless debugging may turn off. Reconnection does not guarantee fixed unattended access over Tailscale; normal mDNS discovery is LAN-local. Only request new pairing if authorization is actually missing/revoked. Codes are transient, not a durable configuration. Do not persist them. Android 17's newer automatic Wi-Fi reconnect behavior must not be promised for this Android 16 phone.

## Contacts

Prefer Google's People API: one-time OAuth with Contacts scope, securely persisted refresh credentials, searchable contact name, duplicate checks, createContact, then people.get readback. Confirm the intended Google identity. This removes phone/debugging connectivity from contact creation; normal Google sync supplies phone contacts. Cloud verification is not proof of completed phone sync.

Android Contacts Provider is another CLI route when authorized. A Google contact consists of a `raw_contacts` row with the intended `account_name` and `account_type=com.google`, plus linked name and phone data rows. Query before insertion. Prefer atomic batches; otherwise track the newly created raw ID, verify every step, and roll back only that record if incomplete. Do not drive the Contacts editor as a fallback.

## Alarms

Google Clock supports Android's SET_ALARM intent (time, label, silent ringtone, vibration, no repeating days for a one-time alarm). It does not provide a documented full alarm-record CRUD/list response through that interface. SHOW_ALARMS opens a screen; it is not a list API. `dumpsys alarm` is system scheduling state, not the user's complete Clock database. A creation request without readback remains unverified.

During research, an established alarm app with a documented data API was considered. Sleep as Android documents an alarm content provider with CRUD and fields for hour, minutes, date/time, enabled, vibration, message and sound; accessing it requires `com.urbandroid.sleep.READ` in the caller's manifest. It is not an authenticated remote HTTP endpoint out of the box: a properly authorized local integration/bridge is still needed. Check silent/vibrate behavior, reboot recovery, offline firing, duplicate prevention and cancellation before promising reliability.

A new clock app is a last resort, not the default recommendation. It would need native exact alarms, persistent records, permissions, boot restoration, vibration handling and tested delivery. A forwarding wrapper cannot add readback to Google Clock's private alarm database. Keep the user's existing Google alarms unless they explicitly authorize an app change.

Sources:
- https://developer.android.com/tools/adb
- https://developer.android.com/reference/android/provider/AlarmClock
- https://developers.google.com/people/api/rest/v1/people/createContact
- https://developer.android.com/reference/android/provider/ContactsContract.RawContacts
- https://sleep.urbandroid.org/docs/devs/content_provider_api.html
- https://developer.android.com/about/versions/14/changes/schedule-exact-alarms

Suntimes source was also reviewed: its alarm provider query supports full settings, but insert returns null and update/delete return zero. Creation goes through an Activity intent. This was not adopted as a proven unattended create/readback route; no Suntimes app was installed.

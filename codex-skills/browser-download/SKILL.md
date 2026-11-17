---
name: browser-download
description: Access authenticated websites and download files using existing Brave sessions or saved logins, including Illinois Canvas and MyMcKinley.
---

# Browser Download

Use this skill for requested access to an authenticated website or file using the user's existing Brave login. On this machine, use a headless browser without disturbing the user's desktop.

If the normal profile's session has expired, use the separate automation profile
at `~/.local/share/codex-browser/profile` with the Playwright environment and
helper documented in `~/dev/config/dotfiles/bootstrap/README.md` under Browser
automation profile. It supports ordinary Playwright browser interactions and
retains website sessions across runs. Run only one automation instance at a
time. The separate profile does not automatically inherit saved passwords or
cookies from the normal profile; authenticate as required and ask the user to
complete MFA or other interaction when necessary. The existing-profile GUI
restrictions below do not prohibit interacting with this separate profile.

## Saved Brave credentials for headless sign-in

The user authorizes use of their saved Brave login to complete their requested
site access. When cookies alone fail, a separate headless Playwright browser can
use the matching saved credential without taking desktop focus. On this Fedora
machine the user's unlocked Secret Service keyring has a `Brave Safe Storage`
entry, and Brave's `Default/Login Data` SQLite database contains saved logins.
Select only the exact target or official SSO origin and account needed; never
dump the database, print credentials, pass them in command-line arguments, or
write them to disk. Keep the password and key in process memory; submit them
only to the verified matching HTTPS login origin. Do not use credentials on
unrelated sites. Do not copy the database or interfere with the live browser.

On 2026-11-11 the university Microsoft entry was readable using a read-only
SQLite URI with `immutable=1` (the live database was otherwise locked), Python
`secretstorage` for the unlocked `Brave Safe Storage` secret, and Chromium's
Linux `v11` scheme: PBKDF2-HMAC-SHA1 with salt `saltysalt`, one iteration and a
16-byte key, then AES-CBC with 16 ASCII spaces as IV and PKCS#7 unpadding. This
is format-specific and may change; check the prefix and fail closed for other
formats. Immutable SQLite can omit uncheckpointed changes, so a missing or stale
entry is not proof no current saved login exists. Do not manipulate browser
locks or copy the database. Never record decrypted values in logs or the model
output. System Python has `secretstorage` and `cryptography`; Playwright is in
`~/.local/share/codex-browser/venv/` when the opt-in setup has been installed.

The test entered the saved username and reached the Canvas course in a separate
headless browser after a Microsoft sign-in redirect. It did not record whether
the password field appeared or was filled; existing SSO state may have helped.
Therefore it did not prove a completely fresh password-only login. Check each
step without logging page secrets, and report accurately whether a password was
submitted. MFA, CAPTCHA, an unavailable keyring or site-specific policies may
still require user action. Do not repeat failed credential submissions.

## Phone approval and navigation

When the requested sign-in requires phone approval, initiate the site's normal
MFA flow in the same headless browser and notify the user on the laptop with
`notify-send`. If the site shows a comparison identifier, include it in the
notification and chat so the user can compare it with their phone before
approving. Do not ask for passwords, one-time codes, or authentication secrets.
Keep the browser and authenticated session alive while waiting; use a bounded
wait and report expiry or rejection. Continue the requested download after
approval without starting another login.

Ålandsbanken e-ID was successfully initiated on 2026-11-13 in a separate
headless Brave instance using the saved username; a laptop notification prompted
phone approval. The saved password was rejected by the separate code-table
login, so do not assume it works or retry failed credentials. e-ID still needs
the user's approval, and a successful login alone did not verify statement
download.

Bank pages can navigate asynchronously after approval and after selecting an
account. An `Execution context was destroyed` error during navigation is not a
failed login: wait for the destination to load and retry the read in the same
session. Handle this both after MFA and after later clicks; keep the browser
open until the requested document has been retrieved and verified. Avoid
unnecessary repeat approval prompts.

## Keep the GUI and credentials untouched

- Do not take over the GUI: do not click, type, navigate, resize, close, or restart the user's Brave window or tabs.
- Do not attach remote debugging to the live browser, launch another browser against its active profile, or copy the profile/cookie database.
- Read only the cookies needed for the requested site and its official SSO provider, use each host's cookies only for that host's requests, and never print, log, serialize, or persist cookie values or authorization headers.
- Before asking the user to sign in, try completing the normal sign-in redirects headlessly using their existing Brave sessions for the requested site and its official SSO provider. Keep cookies scoped to their respective domains and credentials in memory. Retry the requested page after authentication. Ask the user to intervene only if the official flow actually requires fresh credentials, MFA, or consent; a redirect to SSO alone is not sufficient reason to stop.

## Headless Brave session

Brave's default Linux cookie database is:

    ~/.config/BraveSoftware/Brave-Browser/Default/Cookies

Use browser_cookie3 to read the existing Brave cookies for the target host and requests to fetch the URL. If authentication redirects to the site's official SSO provider, load that provider's existing cookies into the same in-memory session with their original domain restrictions. Follow the normal redirects and SSO auto-submit forms, then retry the requested page. For example, for Illinois Canvas:

    import browser_cookie3
    import requests

    cookies = browser_cookie3.brave(
        domain_name="canvas.illinois.edu",
        cookie_file="/home/pt/.config/BraveSoftware/Brave-Browser/Default/Cookies",
    )
    response = requests.get(
        "https://canvas.illinois.edu/courses/COURSE_ID/modules",
        cookies=cookies,
        timeout=30,
        allow_redirects=True,
    )

Keep the cookie jar in process memory. If browser_cookie3 is missing, install it into a temporary /tmp target and set PYTHONPATH for that command; do not change the system Python environment. Remove temporary package files when finished.

For Canvas, inspect the authenticated module or item page for the original file link, then download that link with the same in-memory cookie jar. Keep requests scoped to the requested Canvas content. Do not guess file IDs or substitute previews for the original file.

Check the final response before saving. A redirect to an Illinois sign-in page starts the SSO recovery described above; it does not by itself establish that user intervention is required. Ask the user only if the official flow actually requires fresh credentials, MFA, or consent. Save only to the requested destination, preserve the source filename when useful, and do not overwrite an existing file unless the user asked for replacement. Verify the downloaded file using an appropriate format check, such as the PDF signature and EOF marker.

## Google Drive: persistent access for user-requested file operations

Use `scripts/google_drive.py` for files created or opened by this OAuth app. It uses the existing installed-app Google OAuth client at `~/dev/personal/automation/calendar-llm/credentials.json` and the narrow `drive.file` scope. It stores the separate refresh token in `~/.config/codex-google-drive/token.json` (directory 700, token 600); never print or commit token or client secret. On future runs it refreshes automatically. Commands: `python3 ~/.codex/skills/browser-download/scripts/google_drive.py verify`, `list FOLDER_ID`, or `upload FOLDER_ID PATH`. The scope does not grant blanket access to all existing Drive files; handle 403/404 honestly. Before any write, ensure the user requested it. If auth is absent, revoked or expires, run `auth`, give the user its authorization URL on the same machine, and verify refresh afterward. Google may require reauthorization; never promise permanent access. Restore client credentials and authorize again on a new machine.

The first use encountered HTTP 403 `SERVICE_DISABLED`: the Google Drive API was disabled for the existing OAuth project. Enabling it in that project's Google Cloud Console fixed access. A fresh authorization was needed because the earlier throwaway script discarded its refresh token; use the persistent helper instead. Avoid Google login automation when the OAuth API is available; Google rejected the headless sign-in as an insecure browser.

## MyCarle X-ray imaging

The separate Brave profile can access MyCarle after signing in via the saved `https://www.mycarle.com/` credential: the login is two-step, so fill `#Login`, click `#submit` (Continue), then fill `#Password` and submit. Suppress exception messages from operations containing credentials. Follow any portal verification requirements. In Test Results, select the study and its “Show images” link. The image viewer opens at `chvnapatimg.carle.com` with an outer page stuck on “Loading”; inspect its nested frames. The inner frame loads the images; allow time for it. On Nov 13, the Nov 10 hip study had three images. Its patient-viewer settings reported `h_enableDownload=False` and `h_enableDataDownload=False`, and no original-image export was visible. A viewer screenshot is only a clearly labelled preview, not a DICOM study; request original imaging from Carle when required. Do not send the viewer's “Email Study” form without explicit authorization.

## MyMcKinley appointments

For current appointments, open `https://illinois.medicatconnect.com/home.aspx` in the separate persistent automation profile and read “Upcoming Appointments.” The Appointments menu is for scheduling and may not list existing visits. A saved visit summary or calendar entry is not proof of current portal status.

If signed out, select “Access through your institution,” type `illinois` into `#searchinput` using keyboard events (a simple fill did not trigger results), and select “University of Illinois Urbana-Champaign.” Select the university account on the Microsoft sign-in page. The saved credential for the exact university Microsoft tenant and account worked on 2026-11-17, using the in-memory credential procedure above; follow any MFA prompt and do not repeat a rejected password. After sign-in, return to the portal home page. The automation profile may retain the session, but authentication and its recovery are runtime state and are not restored by the dotfiles installer.

On Nov 13, automatic Drive authorization succeeded without user interaction by reusing the user's already signed-in Brave Google session in a separate ephemeral headless browser, with consent for the exact previously authorized Drive scope. `browser_cookie3` returned zero cookies despite existing Google cookies. A read-only immutable SQLite query of the existing Cookies database found `v11` encrypted entries. Decrypt them in memory using the saved Brave key as above; for modern Chromium's cookie format, strip the leading 32-byte SHA-256 host-key digest only after verifying it matches. Copy only the Google and official OAuth cookies into an ephemeral Playwright context, never a persistent profile or a file. Navigate to the helper's one-time OAuth URL, confirm the Google account, client and requested scope, and complete consent only when the user has authorized that exact access. The loopback callback delivered a refresh token and forced refresh and Drive listing both passed. If Google requests fresh authentication or MFA, do not bypass it.

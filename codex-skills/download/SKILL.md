---
name: download
description: Download user-requested web files into a local folder, especially course materials; use when the user wants files saved locally rather than only opened or summarized.
---

# Download

Save the requested files to the user's intended local destination, preserving a useful folder structure and existing files.

- Infer the destination from the current course or project context when clear. Otherwise ask for the destination before downloading.
- Inspect the destination and source page first. Reuse an existing download script or established naming/layout convention when available. Do not overwrite existing files unless the user asked to replace them; prefer fetching only missing files.
- Download the original files from their source URLs. Do not substitute page summaries, previews, or converted content when the user asked for the files themselves.
- For login-protected materials, open the official login page and let the user authenticate. Never ask for or handle their password. Continue only through the normal signed-in browser/session or official download mechanism; do not bypass access controls or DRM.
- After downloading, verify each file is complete with an appropriate lightweight check (for example, PDF signature and EOF marker, or media metadata) and report the destination and any files that could not be fetched.

## Network and DNS failures

If a download fails with a DNS resolution error such as `Temporary failure in name resolution`, treat it as a problem with the current Codex session's network state, not proof that the source file is missing. Tell the user to restart the Codex session, then retry the same download after they resume. Do not keep retrying in the failing session or ask them to repeat the task details. Distinguish DNS failures from HTTP errors, permission restrictions, and login redirects; those require different handling.

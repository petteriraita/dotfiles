---
name: medical-visits
description: Create or edit doctor, physiotherapy, surgery, and nursing visit records in the user's Obsidian health vault and verify they appear in the local health dashboard. Use for dedicated appointment notes; not for daily health updates or general medical questions.
---

# Medical Visits

Write records under `/home/pt/dev/obsidian_vault/2 - Areas/medical/conditions/hamstring2025/Visits`.

The dashboard parser requires YAML frontmatter at byte zero. Never put a resume block, timestamp, heading, blank line, or byte-order mark before the opening `---`.

Use exactly these metadata fields, matching the surrounding records:

```yaml
---
date: "YYYY-MM-DD"
type: "physiotherapy"
clinician: "Name"
clinic: "Clinic"
evidence: "patient_report"
---
```

- Valid types: `doctor`, `physiotherapy`, `surgery`, `nursing`.
- Valid evidence: `clinical_record`, `patient_report`, `mixed`, `translation`.
- Leave an unknown value blank rather than guessing. The encounter date must come from evidence, not merely the filename or file timestamps.
- Use `## Summary`, `## Date evidence`, `## Record`, and `## Source`. Keep Summary concise; preserve relevant detail and uncertainty in Record; link or identify the source precisely.
- Distinguish the patient's report from a clinical record. Do not create diagnoses or treatment advice.
- Match the filename `YYYY-MM-DD - type - clinician.md`; use `Undated` or `clinician unrecorded` when genuinely unknown.

After every write, run:

```sh
python /home/pt/.codex/skills/medical-visits/scripts/validate_visit.py --dashboard "/absolute/path/to/visit.md"
```

Success requires both local schema validation and the corresponding `sourcePath` from `http://127.0.0.1:4173/api/visits`. If the dashboard is not running, start `/home/pt/dev/health-stats-dashboard` with `npm start`, then rerun validation. Do not report completion when the API does not contain the record.

---
name: health-context
description: Answer questions about the user's personal health, recovery, physiotherapy, symptoms, appointments, or medical history by first using their private local health dashboard. Do not use for unrelated general health questions.
---

# Health Context

Use the private local health dashboard as the source of context for questions about the user's health.

For a request to verify a current MyMcKinley appointment, also use the `browser-download` skill to check the live portal; stored visit summaries and calendar entries may be outdated.

The dashboard normally runs as an always-on systemd user service. Check it first:

```sh
systemctl --user is-active health-stats-dashboard.service
```

If it is inactive, start it with `systemctl --user start health-stats-dashboard.service`. The project is at `/home/pt/dev/personal/apps/health/health-stats-dashboard`.

Use the relevant local view:

- `http://127.0.0.1:4173/` — charts, daily signals, diary data, and doctor/physio visits.
- `http://127.0.0.1:4173/raw-data.html` — human-readable focused daily tables; Hip recovery is the default.
- `http://127.0.0.1:4173/api/raw-daily-data?view=hip&range=recent` — default AI source for hip recovery. It covers one month before surgery through today and contains steps, pain measures, and hip/physio notes only.
- `http://127.0.0.1:4173/api/raw-daily-data?view=hip&range=all` — older hip history. Read this only when the question requires the preoperative or legacy course.
- `http://127.0.0.1:4173/api/raw-daily-data?view=gut` — meaningful gut, stool, food, energy, and mood history.
- `http://127.0.0.1:4173/api/raw-daily-data.csv?view=hip&range=recent` — CSV form; change the query parameters for the other focused datasets.
- `http://127.0.0.1:4173/api/ai-context` — compact reviewed case narrative plus the live hip/hamstring log.

For hip, recovery, or physiotherapy questions, read the recent hip JSON first. Prioritize the latest weeks: exercises and dose performed, walking/step load, pain during or after activity, and later or next-day pain response. Use those observations to assess trajectory and load response and to discuss possible exercise adjustments. Read `/api/ai-context` for the operation and established background, the legacy hip view only when older chronology matters, and visit records from `/api/visits` when appointment detail matters.

For gut questions, use the gut JSON instead of loading hip recovery data. Treat missing values as missing, not zero. Distinguish the user's daily reports from documented clinical records and do not imply that an observed association proves causation.

When creating or editing a doctor, physiotherapy, surgery, or nursing visit in the dashboard's `Visits` folder, use the `medical-visits` skill. Its frontmatter and live-API validation are required; a file existing in Obsidian is not enough to establish that the dashboard can read it.

Keep this information local. Do not edit health records, share them, or contact anyone unless the user explicitly asks.

## Expert Blind-Spot Check

For consequential recovery, symptom, treatment, or return-to-activity questions, end the user-facing response with a brief **What a clinician would flag** section. Surface one to three material considerations the user did not ask about, including alternative explanations, missing measurements, load interactions, or signs that warrant professional assessment. Clearly separate observed data, inference, and medical uncertainty. Skip it for simple record retrieval or routine status summaries when no additional issue would change the user's action.

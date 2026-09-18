---
name: health-context
description: Answer questions about the user's personal health, recovery, physiotherapy, symptoms, appointments, or medical history by first using their private local health dashboard. Do not use for unrelated general health questions.
---

# Health Context

Use the private local health dashboard as the source of context for questions about the user's health.

If it is not already running, start it in a persistent terminal:

```sh
cd /home/pt/dev/health-stats-dashboard
npm start
```

Then open `http://127.0.0.1:4173/` and use the relevant part of the site: daily signals and diary data, doctor/physio visits, or AI case history. The site also links to its live AI context when a compact text view is useful.

Keep this information local. Do not edit health records, share them, or contact anyone unless the user explicitly asks.

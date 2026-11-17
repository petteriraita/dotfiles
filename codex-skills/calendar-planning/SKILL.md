---
name: calendar-planning
description: Build realistic daily or weekly time-block plans from the user's calendar, tasks, priorities, and routines. Use when asked for an optimal schedule, study plan, deep-work blocks, or weekly planning; not for simply listing calendar events.
---

# Calendar Planning

Plan work, not just appointments. Read live calendar and task sources before proposing a schedule. When email is available and relevant, scan for time-sensitive obligations before ranking the day; verify urgent claims by reading the messages. For university work, use the `school` skill to verify registration, deadlines, assignment state, and the actual next step. Use the latest user-stated constraints, such as meal windows, mobility, or temporarily skipping class; scheduled events can be context without being commitments to attend.

When the user asks you to create or write out a daily, weekly, or multi-day schedule, add the planned time blocks to Google Calendar as well as presenting the schedule in chat. Treat this as standing authorization for those schedule blocks; do not ask again. Do not add blocks when the user only asks to list, inspect, or discuss existing events. Preserve existing events and avoid duplicate blocks. If a schedule block is only a tentative option or depends on an unverified assumption, label it as tentative in the event title or leave it out and explain that choice.

## Add schedule blocks to Google Calendar

- Read the calendar first and reconcile the proposed blocks against existing events. Create events only for the new planned work blocks, meals, or other blocks the user would benefit from seeing; do not recreate existing classes or appointments. Use the user's local timezone (`America/Chicago`) and the plan's stated local times.
- Use the existing Calendar API write authorization in `/home/pt/dev/personal/automation/calendar-llm/token-calendar-write.json`. In the `calendar-llm` conda environment, load it with `google.oauth2.credentials.Credentials.from_authorized_user_file(..., ['https://www.googleapis.com/auth/calendar.events'])`, then build `googleapiclient.discovery.build('calendar', 'v3', credentials=creds)`. Insert each event with `service.events().insert(calendarId='primary', body=event).execute()`. For a timed block, set `summary`, optionally a short `description` with the intended output, `start: {dateTime: 'YYYY-MM-DDTHH:MM:SS', timeZone: 'America/Chicago'}`, and matching `end` fields. Use the existing token; do not print credentials or token contents.
- Make each title specific (for example, `CS 425 midterm practice — timed problems`). Never invent missing times or imply attendance at an event the user said they are skipping. Keep transition and travel assumptions out of calendar unless explicitly included in the plan.
- After inserting, fetch the created event IDs and verify the saved title, local start/end, and date. Report that the schedule was added, and mention any blocks that could not be added. If the API write fails, still provide the schedule and explain the failure clearly.

Current personal meal timing: breakfast is 8:00–9:00 AM on weekdays and 8:50–9:50 AM on weekends; lunch is 12:00–1:00 PM and dinner is 5:00–6:00 PM. Reserve the full hour for each meal. Check `/home/pt/dev/personal/knowledge/obsidian_vault/current habits.md` for later changes before building a detailed day plan.

Reserve a protected one-hour physio/gym block in each daily plan. An existing one-hour physiotherapy appointment can satisfy it; avoid duplicate blocks. The hour is a scheduling allowance for the current rehabilitation program, not a requirement to exercise continuously or increase the prescribed dose. Fit it around meals and appointments.

## Decide what earns time

- Start with immovable commitments, true deadlines, recovery needs, and practical travel or setup time. Distinguish confirmed times from assumptions. Do not invent a wake time or travel duration; when unknown, use a clearly conditional departure time.
- Rank work by deadline, consequence, importance, and current progress. Check whether a task actually applies to the user. Give the highest-value demanding work the best uninterrupted hours. Match lower-energy periods to named admin, review, or logistics tasks.
- Distinguish **deep work** (proofs, problem solving, writing, coding, active exam practice) from **light work** (email, payments, organizing materials, checking requirements). A deep block should name the course/project and a concrete deliverable or question. Do not fill open space with generic “study,” “catch up,” or “light work.”
- Use roughly 60–90 minute deep blocks when the day supports them, but make durations fit meals, appointments, task size, and the user's stamina. Short transitions are fine; add longer recovery only when there is a reason. Do not interrupt useful work merely to make a tidy schedule.
- Reserve enough time to finish or make a meaningful checkpoint before a deadline. If the workload exceeds the day, say what is being deferred and why. Prefer a realistic plan to a maximally packed one.
- Treat focused school blocks as protected time: keep work on the same assignment together where practical, and avoid placing brief admin or review tasks between related deep-work blocks. Batch email, reflection, task review, and similar maintenance into one bounded block when their timing allows. Add another admin block only when a deadline or real dependency warrants the interruption.
- The user's usual school-work cutoff is **8:00 PM**. Plan to finish school by then, leaving the evening free, unless the user explicitly chooses a later session or a hard deadline requires discussing an exception. An 8:50 AM weekend breakfast does not preclude a 7:50–8:50 AM first activity if the user is ready; do not assume a later start simply because breakfast is later, and do not invent a wake time.

## Daily plan

Provide chronological time blocks with a specific action and intended output. Put mandatory small tasks together in one or a few light-work blocks when their deadlines allow. State when to check email and review tasks, if at all: use a bounded triage block, prioritize known urgent actions, and protect deep blocks from open-ended inbox work. A targeted check for an expected confirmation can differ from a full inbox scan. Include meals and travel or preparation around appointments. Give a clear stopping point and a small replanning rule if a deep task runs long. If a proposed block depends on an unverified assignment or travel time, state that dependency beside the block and provide a concrete fallback.

## Weekly plan

Work backward from deadlines and fixed events. Assign each major project enough deep-work blocks across the week, with explicit milestones and time for review or submission. Choose which days should carry heavier deep work and which have appointments or other constraints. Batch small mandatory/admin tasks on one suitable day when possible, while keeping time-sensitive tasks on their actual due days. Leave capacity for changes; do not treat a single admin day or 90-minute block as a rigid rule.

The approach draws on Cal Newport's [daily time blocking](https://calnewport.com/deep-habits-the-importance-of-planning-every-minute-of-your-work-day/) and [weekly planning](https://calnewport.com/deep-habits-plan-your-week-in-advance/): use weekly priorities to choose daily blocks and revise the plan when reality changes.

## Expert Blind-Spot Check

When a plan involves meaningful tradeoffs, deadlines, recovery constraints, or uncertain dependencies, end the user-facing response with a brief **What an expert would flag** section. Surface one to three non-obvious issues that could invalidate the plan, including when the user's stated priority or sequencing is strategically weak. Prefer a concrete adjustment or validation step. Skip it for straightforward scheduling when there is no material blind spot.

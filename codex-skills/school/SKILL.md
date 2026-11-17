---
name: school
description: Get current context for the user's university courses, upcoming deadlines, assignment progress, and next steps, and record course exam dates. Use for $school, school planning, exam calendar updates, or work on one of the user's courses; not for unrelated general tutoring.
---

# School

Use live sources to orient to the user's current term. The skill is a map to those sources, not a snapshot of coursework.

## Where to look

- Course and progress notes: `/home/pt/dev/personal/knowledge/obsidian_vault/1 - Projects/`. The current term is `/home/pt/dev/personal/knowledge/obsidian_vault/1 - Projects/uiuc_fall_2026/`; discover a newer term there when appropriate. Each course has `main_page.md`, with `Exercises/`, `Exams/`, and sometimes `Lectures/` as needed.
- Read each course's `main_page.md` for the user's actual registration and credit level before deciding which assignments apply. Store confirmed course-specific facts there so the user does not have to repeat them. CS 425 is 3 credits in Fall 2026, so its 4-credit-only MPs do not apply.
- Live schedule and tasks: run `conda run -n calendar-llm python /home/pt/dev/personal/automation/calendar-llm/pull_all.py 14` for a two-week view of Google Calendar, Google Tasks, and Todoist. It reads all visible calendars and open tasks. Use Calendar events to understand commitments and available time; identify school deadlines from task titles and course sources. If one section reports an error, say which source is unavailable and use the working sections. For direct Google Tasks reads or requested changes, follow the `google-tasks` skill.
- Google Tasks dates are date-only; get deadline times and assignment requirements from the current course source linked by `main_page.md` or the assignment itself. Do not infer a submission time from the task date.
- Course work: follow paths and links in the relevant exercise note to the assignment specification and working repository. Check actual files, tests, or output when progress matters.

## Orient and answer

For daily or weekly time-block plans, also follow the `calendar-planning` skill for current meal windows, focused-work blocks, and the user's planning preferences.

Include a protected one-hour physio/gym block in each daily school plan, fitting it around appointments and meals. Count an existing one-hour physiotherapy appointment toward this block rather than adding a duplicate. This reserves time for the current rehabilitation program; it does not prescribe an hour of exercise or increase the exercise dose.

For `$school` alone, give a compact snapshot: current courses, overdue and upcoming school deadlines (normally the next 14 days), relevant calendar commitments, work with credible evidence of activity, and the most useful next actions. For a named course or assignment, focus on that scope. Read relevant `main_page.md` files first, then only the exercise or lecture notes needed for the request. Do not treat every pre-created exercise or lecture note as active work.

When giving the user a local course file path, show it as plain, terminal-ready inline code using `~/` in place of `/home/pt/` (for example, `~/dev/school/uiuc/2026-fall/CS_425_Distributed_Systems/week_03/L3.FA26.pdf`). Do not provide only the absolute path or format the path as a clickable link.

Treat `date` in exercise frontmatter as a note date, not a due date. Many exercise stubs contain `estimate_time_left_hours: 6`, `missing_parts_string: everything`, empty `next_steps_string`, or generic checkboxes. These are placeholders until corroborated by the note body, a current assignment, or the working repository. Zero estimated hours does not mean done when missing parts remain. `model_answers_checked_B` tracks later solution review, not assignment submission. If status or deadline is unverified, say so plainly; do not report a complete schedule when Google Tasks is unavailable.

If Google Tasks and course materials disagree, show both dates and their sources, then verify the current course source before planning around a deadline. Course notes may contain old dates or links, so check the source when accuracy matters. Distinguish work completed, submitted, and model answers reviewed.

## Current planning constraints and feedback

The user confirmed on 2026-11-05: **Saturday school/admin work stops at noon**; protect the afternoon/evening for board games/social time. Fit study and the protected physio allowance into the morning instead of filling the afternoon with catch-up work.

When planning, read the latest entry in `/home/pt/dev/personal/knowledge/obsidian_vault/School planning reflections.md` for plan-versus-actual feedback. Use actual progress to scale checkpoints; do not treat old time estimates, drafted answers or a moved task date as proof of completion or an official deadline extension.

## Keep progress useful

For a midterm, final, or other course exam, create or update one dedicated note in that course's `Exams/` folder when recording its date, scope, instructions, preparation status, or next steps. Include the exam's topic and date in its filename, link the source, and distinguish confirmed from tentative details. Put exam-specific material and progress there. Keep `main_page.md` as a course overview with a short link to the exam note; move exam-specific material out of the main page if it was placed there earlier. Check for an existing matching exam note before creating another.

When the user asks to record progress, or when course work in the current request changes what has been done, update the matching exercise note in place. Preserve its YAML fields and existing structure. Keep `Current Status` to what actually happened, `Next steps` to a short actionable checklist, `missing_parts_string` and `next_steps_string` consistent with those sections, and `estimate_time_left_hours` only when there is a grounded estimate. Put test results, blockers, source links, and repository paths in `Notes` or `References` as appropriate. Do not mark work submitted, complete, or reviewed without evidence.

Keep deadlines in Google Tasks and progress in Obsidian. Do not silently create or change tasks when updating an exercise note; change Google Tasks when the user requests deadline tracking or a correction, and follow the `google-tasks` skill for that operation.

## Expert Blind-Spot Check

For consequential academic choices, administrative requirements, research planning, or workload decisions, end the user-facing response with a brief **What an expert would flag** section. Surface one to three material considerations the user did not ask about, including when their assumed process, timing, prerequisite, or definition of success may be wrong. Distinguish confirmed requirements from professional judgment, and prefer a concrete verification or alternative over generic caution. Skip this section for simple factual lookups or mechanical updates when it would add no value.

## Exam dates in Calendar

When the user asks to add a course exam date, put a red all-day exam event on that date, titled with the course and exam topic. Also find the matching scheduled class meeting on that date, if one exists, and make that single occurrence red with `Exam: <topic>` in its title. Keep its original time and location and leave the rest of the recurring class series alone. Check existing exam events, including an old date when the user corrects one; move or update them instead of creating duplicates. Confirm the event color against the Calendar event palette (Google's red event color is currently ID `11`). An all-day event uses a calendar `date` start and the following date as its exclusive end, not a timed midnight event. If a calendar connector cannot preserve that format, use the existing Calendar API write connection in `/home/pt/dev/personal/automation/calendar-llm/` and verify the saved event. If no class meeting matches, still add the all-day exam and report that no class occurrence was changed.

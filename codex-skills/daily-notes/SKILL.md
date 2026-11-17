---
name: daily-notes
description: Add dictated, transcribed, or written health and food updates to the user's Obsidian daily notes without changing their schema or adding narrative outside YAML. Use for food_notes, hip_notes, nose_notes, and the daily health metrics; not for general Obsidian notes.
---

# Daily Notes

Update daily notes in `/home/pt/dev/personal/knowledge/obsidian_vault/3 - Resources/daily notes`.

- Preserve every unrelated YAML value and body section. Change existing plan or reflection sections only when the user asks for them.
- Put health information only in existing YAML keys. Never add headings, transcript sections, comments, resume commands, or new YAML keys for health updates.
- Route food and gut details to `food_notes`, hip/hamstring recovery and physiotherapy details to `hip_notes`, and nasal details to `nose_notes`. Use only `hip_notes`; never create or restore the retired `hamstring_notes` key. Fill health scalar metrics only when the user states them clearly; do not infer missing health values.
- If the user gives a study interval and break durations but no exact Pomodoro count, estimate `deepwork_pomodoros_30` from focused work time in 30-minute units and say it is an estimate. Subtract stated breaks; allow for other pauses when the account suggests them. Record `programming_pomodoros_30` separately from stated programming time or counts; these are included in, not added to, the total deep-work count. Do not turn general elapsed time into a claim of uninterrupted focus.
- Keep the user's first-person wording and level of detail. For speech transcripts, remove filler and repetition and fix clear recognition errors, but do not turn the entry into clinical prose or add interpretations.
- Before recording a health number, read `/home/pt/dev/personal/knowledge/obsidian_vault/2 - Areas/medical/conditions/IBS/health data standards.md` and use its definitions. Preserve distinctions such as pain at a specific time versus `hip_morning_pain` or `hip_prev_night_pain`.
- Choose the note from the event or recording's capture date, not the date a file was copied or transcribed. If that day's note is absent, create it from `/home/pt/dev/personal/knowledge/obsidian_vault/3 - Resources/5 - Template/daily template.md`; clear prefilled health defaults that the source does not establish, then change only the relevant existing YAML values.
- Keep YAML valid. Quote a string when punctuation could be parsed as YAML syntax.
- Write `food_notes`, `hip_notes`, and `nose_notes` as plain YAML text without quotes when valid. Quote only when the content requires it for correct YAML parsing, such as a leading YAML indicator, `: `, ` #`, or a value that YAML would otherwise treat as a different type.
- Interpret `mouth_taped_yesterday` by the health data standard: `y` means tape was on this morning, `n` means it was not. Do not infer `stool_form`, nasal airflow, or spray use from a general symptom description or a template default when creating a note.
- When the user asks for daily planning or reflection, fill the existing plan and reflection sections below YAML; the YAML-only rule applies to health updates. Mark checklist items complete only when the user says they were done.
- If the user asks to track a deadline discovered while processing daily notes, create or update its task in the user's task service after checking for duplicates, and record the verified deadline time in the task title or notes. Do not add a new YAML key for deadlines.
- In the final response, briefly identify any requested source, message, or detail that could not be found or verified; do not imply those parts were completed.

The no-content-outside-YAML rule for health updates is an explicit exception to any general Obsidian-note convention that would add a conversation resume block.

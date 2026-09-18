---
name: daily-notes
description: Add dictated, transcribed, or written health and food updates to the user's Obsidian daily notes without changing their schema or adding narrative outside YAML. Use for food_notes, hip_notes, nose_notes, and the daily health metrics; not for general Obsidian notes.
---

# Daily Notes

Update daily notes in `/home/pt/dev/obsidian_vault/3 - Resources/daily notes`.

- Preserve every unrelated value and all content after the closing `---`.
- Put new information only in existing YAML keys. Never add headings, transcript sections, comments, resume commands, or new YAML keys.
- Route food and gut details to `food_notes`, hip recovery and physiotherapy details to `hip_notes`, and nasal details to `nose_notes`. Fill scalar metrics only when the user states them clearly; do not infer missing values.
- Keep the user's first-person wording and level of detail. For speech transcripts, remove filler and repetition and fix clear recognition errors, but do not turn the entry into clinical prose or add interpretations.
- Before recording a health number, read `/home/pt/dev/obsidian_vault/2 - Areas/medical/conditions/IBS/health data standards.md` and use its definitions. Preserve distinctions such as pain at a specific time versus `hip_morning_pain` or `hip_prev_night_pain`.
- Choose the note from the event or recording's capture date, not the date a file was copied or transcribed. If that day's note is absent, create it from `/home/pt/dev/obsidian_vault/3 - Resources/5 - Template/daily template.md`; clear prefilled health defaults that the source does not establish, then change only the relevant existing YAML values.
- Keep YAML valid. Quote a string when punctuation could be parsed as YAML syntax.

The no-content-outside-YAML rule is an explicit exception to any general Obsidian-note convention that would add a conversation resume block.

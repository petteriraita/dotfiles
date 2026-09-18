---
name: obsidian-notes
description: Create or edit Markdown notes in the user's Obsidian vault, matching their compact personal-note style. Use for requests to save, document, organize, or update information in Obsidian; not for ordinary Markdown files outside the vault.
---

# Obsidian Notes

Write useful memory aids, not polished documentation.

## Vault

The vault's absolute path is `/home/pt/dev/obsidian_vault`.

Before creating a note, search filenames and content for an existing note on the same topic. Update the existing note when it is the natural home; otherwise create a plainly named `.md` file in the vault root unless the user specifies a folder. Do not reorganize other notes.

## Resume line

For ordinary unstructured notes, add or update a fenced code block at the top containing the command for resuming the current Codex conversation:

```text
codexa CURRENT_CONVERSATION_ID
```

Use the actual current conversation ID; never copy an ID from an example or another note. If the ID is not explicitly available, take a distinctive exact phrase from the user's current message and run:

```sh
/home/pt/.codex/skills/obsidian-notes/scripts/find-codex-session-id 'distinctive exact phrase'
```

The helper searches `/home/pt/.codex/sessions` and prints the session ID from the newest matching transcript. If there is no unique match, inspect the matching files instead of guessing.

Never place a resume block before YAML frontmatter. Machine-read structured notes must retain `---` as the first bytes of the file. In particular, use the dedicated `daily-notes` or `medical-visits` skill for daily notes and health visit records, and do not add a resume block unless that schema explicitly provides a field for it.

## Style

- Be terse. Aim for roughly half a screen or page and never exceed one page unless the user asks or the necessary source material cannot fit.
- Use the filename as the title; do not repeat it as an H1.
- After the resume block in a new note, add `### YYYY-MM-DD HH:mm`, using the local time.
- Do not add YAML frontmatter, `Tags:`, aliases, status fields, or decorative metadata unless the user requests them or the destination note already relies on them.
- Prefer short prose, commands, and small lists. Add headings only when they make retrieval faster.
- Preserve exact commands, absolute paths, IDs, URLs, and other details needed to act later.
- Omit background, repeated explanations, generic cautions, and empty sections.
- Use `[[wikilinks]]` only for clearly relevant notes that already exist. Do not invent a linking scheme.
- When editing an unstructured note, preserve its established format and refresh an existing resume command at the top. Do not force this convention onto a structured collection whose schema or parser requires something else.

## User communication

While working, give at most one short status sentence. Afterward, report the note's absolute path and summarize the material change in one or two sentences.

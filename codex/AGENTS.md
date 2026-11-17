# Personal Codex skills

When the user asks to create, update, or remove a personal Codex skill, use `$skill-creator`.

For a personal skill, keep its canonical folder in `/home/pt/dev/config/dotfiles/codex-skills/`, expose that complete folder through a symlink in `/home/pt/.codex/skills/`, validate it with the built-in skill creator's `quick_validate.py`, and update `/home/pt/dev/personal/knowledge/obsidian_vault/Codex skills.md` with its title, short description, and canonical `SKILL.md` path. Then explicitly notify the user that its description is also saved in Obsidian. Update `making a Codex skill.md` only if this shared workflow changes.

# Reproducible workstation changes

For durable workstation changes (app settings, keyboard/shell/editor configuration, services, tools, workspace layout, and new personal/course repositories), use `$dotfiles-bootstrap` and update the reproducible setup path in the same task. The entry point is `/home/pt/dev/config/dotfiles/install.sh`. Ordinary source edits inside existing repositories do not require bootstrap changes. Record authentication, data-backup, or hardware limitations explicitly; do not claim a live-only setting is reproducible.

# Copyable local paths

When showing local filesystem paths to the user, write the complete, copyable path in inline code, not a Markdown hyperlink or shortened label. Replace `/home/pt/` with `~/`. For example: `~/dev/config/dotfiles/codex-skills/browser-download/SKILL.md`. Keep paths outside the home directory absolute. This applies to chat responses; preserve functional links inside documents.

# Plain chat styling

In chat replies, avoid Markdown bold and italics (`**`, `__`, `*`, `_`) because the user's terminal renders emphasized text in pink. Use plain text for emphasis. Do not use HTML color tags; the chat shows them literally.

# Finish earlier work before new requests

When the user sends additional work while a task is in progress, keep the earlier task active and finish it before proceeding to the new work. Incorporate corrections to the current task immediately, but queue separate requests in arrival order. Do not silently abandon unfinished work when a new message arrives. If an earlier task requires user input or an external change, state what remains blocked and retain it as pending while completing independent queued work. Stop or replace a task only when the user explicitly cancels it or asks to change priorities.

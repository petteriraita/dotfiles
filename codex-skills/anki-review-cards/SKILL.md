---
name: anki-review-cards
description: Draft, check, and stage personal Anki cards in the local review-first Add window. Use for “clozify”, “clocheck”, or requests to make Anki cards; not for ordinary explanations of a topic.
---

# Anki Review Cards

Create recall prompts that are small, specific, and worth reviewing. The user’s existing cards show that concrete cues and one compact target are more durable than isolated numeric facts, vague prompts, and bundled facts.

## Stage cards for review

The local bridge queues a card for the next manually opened Anki Add window, or fills one that is already open. It does not focus Anki, send keyboard input, select a deck or note type, or save a note. The user reviews and accepts with `Ctrl+Enter`.

When the request is to make or clozify cards, stage each finished card with `scripts/queue_card.py` unless the user asks for text only. Use `--field` once for a Cloze note and twice for a Basic note. The user controls the current deck and note type in Anki; never change either. If the bridge is unavailable, start Anki with `flatpak run net.ankiweb.Anki`, allow it to initialize, and retry staging. If it remains unavailable, report the problem briefly and still give the drafted cards. Do not save the card or alter the user's deck or note type.

Do not stage cards merely because an answer contains a fact. Stage them when the user asks for Anki cards or uses `clozify`.

## Card design

- One card should test one answerable idea. Split multi-step processes, paired facts, or several independent values.
- Give enough domain and grammar to make the recall target unambiguous. Avoid prompts whose only cue is an isolated number unless that number is genuinely useful and has a stable association.
- Prefer definitions, consequences, mechanisms, discriminations, and usage cues over trivia or decorative wording.
- Keep the answer short. Put necessary context outside the deletion rather than making an oversized blank.
- Do not hide the named term or acronym when the goal is to learn its meaning. Hide the definition, property, or usage clue.

## `clozify`

For each cloze, use exactly one deletion with index `c1`. The deleted text must be at most three words. Put every card in its own fenced code block and stage the same text in Anki’s Cloze field.

- Start the sentence lowercase unless its first word is a proper noun.
- Use MathJax for non-ASCII mathematical or technical notation: for example `\( A^{-1} \)`, not Unicode superscripts or glyphs.
- Think from the learner’s perspective: after the blank is hidden, the remaining sentence must provide a real retrieval cue. (just write the non clozed part to your internal chain of thought and then realize, if this particular prompt might lead to multiple different "right" answers and therefore, the recall for particular answer is impossible)
- if you have more caveats that is important to say, then just add them after the codeblock to the backside with italic
- also keep the 'a, the, an' inside the clozed area since it gives away info if I see it

example: when user tried to learn what the word desideratum means.

Good: `in LLM models, a desideratum is {{c1::a requirement}}`

Bad: `in LLM models, a {{c1::desideratum}} is a requirement`

the bad cloze opens up infinite number of things that could be a "requirement", so therefore, the cloze is not good

## `clocheck`

Begin with exactly one diagnosis: `fully correct`, `small refinement`, or `clear thinking problem`.

Judge accuracy first, then whether the surviving text makes the target answerable and follows the cloze constraints. If a revision is needed, explain the specific flaw concisely and finish with one corrected cloze in its own code block. Do not restate an already-good cloze in a code block. Stage a corrected card only if the user asks to create or replace it.

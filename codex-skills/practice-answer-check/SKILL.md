---
name: practice-answer-check
description: Score a student's submitted practice or assignment answer from 0 to 100 and give brief feedback on whether another attempt would help. Use for requests to check an attempted answer; not for solving an unanswered problem.
---

# Practice Answer Check

Compare the student's answer with the actual question and give a score from 0 to 100 for correctness and completeness. Ignore spelling and phrasing mistakes unless they change the meaning. Do not equate a missing final notation with a conceptual misunderstanding.

Return the score first, then one or two short sentences. For answers with
labeled subparts (such as (a), (b), and (c)), give a separate 0–100 score for
each subpart rather than only an aggregate score. Keep the feedback brief.

Check the whole attempted answer in order, from the beginning, including any
unfinished work. If every attempted step is correct, explicitly say
"Everything written so far is correct" and distinguish an unfinished answer
from a complete one. Do not describe only a range of correct lines in a way
that leaves the rest of the attempt ambiguous. If any step cannot be verified,
say exactly what remains uncertain rather than claiming everything is correct.
If an error or missing step exists, pinpoint the first one. When the answer is in a local file, inspect the
current file and report its absolute line number; do not guess or use relative
line numbers. If only pasted text is available, quote the exact step instead
of inventing a file line number. For a missing step, identify where it belongs.
After verifying every preceding relevant step, explicitly say: "ALL lines above
this one are correct." If any earlier line cannot be verified, state that
uncertainty instead of claiming it is correct. Do not imply the later lines
have been checked or are correct merely because the first error was found. Name its exact question number or subpart in the feedback (for
example, “Try again on (b)”). Base the correction or hint on that step rather
than listing every downstream error. If a later subpart depends on an earlier
mistake, say which part to fix first and which later part to update. If the
reasoning is correct, say so instead of inventing a mistake.

- If the reasoning is essentially correct, say "No need to redo" and directly name any tiny finishing step. Do not manufacture a new exercise.
- If a substantive error would be useful to work through, say "Try again" and explicitly name the subpart(s) to retry, followed by one specific hint aimed at the first error. Let the student do the correction; do not give a vague retry instruction.
- If the remaining issue is mechanical or the value of retrying is low, state the correction directly and say "No need to redo," even if the answer is incomplete.

Calibrate the number to the actual work shown: reserve 100 for a complete correct answer; keep mostly correct answers high; lower it substantially for a central conceptual error. Do not penalize a student twice for the same mistake. Do not reveal the full solution unless the student separately asks for it.

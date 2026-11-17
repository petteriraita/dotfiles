---
name: latex-assignment-report
description: Create or update concise LaTeX assignment-report skeletons from assignment instructions, with full assignment text embedded in the editable document and clearly marked code-only questions.
---

# LaTeX Assignment Report

Create a self-contained working LaTeX document: the user must be able to read
the assignment and work on it directly in the `.tex` file. Embed the actual
question text, necessary setup, subparts, equations, figures, and relevant
implementation instructions. Hyperlinks are supplementary references, never a
substitute for the assignment text. Blank solution environments are expected;
blank prompts, heading-only outlines, and link-only documents are not.

## Before writing

Read the assignment instructions or README to identify every question and its
type. Use the following package set in every LaTeX file created or rewritten by
this workflow:

By default, create course deliverables under the matching course folder in
`~/dev/school/<school>/<term>/<course>/`, following the existing repository
layout (for example, an exam report belongs in an exam or midterm subfolder).
Use the Obsidian course note to identify the assignment and update its rough
time estimate and missing work, but do not store the generated deliverable in
the vault unless the user asks for that location. If the user specifies a
different destination, use it.

```tex
\usepackage{graphicx}
\usepackage{caption}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{enumitem}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{algorithmic}
\usepackage[framemethod=tikz]{mdframed}
\usepackage[a4paper,top=1.5cm,bottom=1.7cm,left=1.6cm,right=1.6cm]{geometry}
\usepackage{xcolor}
```

Use these packages as a baseline only; do not copy unrelated document content
or structure from elsewhere.
Copy the wording of every included assignment question exactly. Never paraphrase,
shorten, or silently change the question, its setup, subparts, mathematical
notation, or figure labels. LaTeX syntax and typography may differ where needed
to render the same content. Check transcribed text against the original PDF or
source, especially around equations, figures, and page breaks. If something
cannot be reproduced faithfully, identify that omission in the final response.
Include original figures referenced by a question. Inspect rendered PDF pages
for figures that text extraction may miss, and extract embedded images where
possible instead of redrawing them.
When updating an existing report that uses custom `enumerate` labels, ensure
`enumitem` is loaded before using options such as `[label=\arabic*)]`.

use \( \) and \[ instead of the dollr signs

when you make the tex, find the corresponding document from obsidian (etc: /home/pt/dev/personal/knowledge/obsidian_vault/1 - Projects/uiuc_fall_2026/MATH_487_Advanced_Engineering_Math/Exercises/problem_set_04.md)
and then go there write down the rough estimate for how much time it takes. then also for missing parts write down like (solve questions 1 - 24)

If an image or other content may have been transcribed inaccurately, tell the
user to open the original; put its absolute path on its own line so it can be
copied easily.

## Matching textbook questions

For each assignment question, look for the same question in the available
Arora–Barak or Sipser textbook PDFs. When found, add a compact reference beneath
its heading with the book title, edition or draft, exercise number, and exact
1-based PDF page number (counting the first page of the file as page 1), not the
printed page number. Identify the exact PDF file in the report source or the
assignment note, since pagination varies between editions and scans. Verify the
match and page against the rendered PDF; do not infer a fixed pagination offset.
Distinguish an equivalent exercise from a merely related theorem or topic, and
do not label related background as the same question. If no matching question is
found, leave the prompt intact and report which questions have no verified
match. Keep references outside the prompt and solution environment; preserve
blank solutions and existing answers. For code-only questions, retain the full prompt in the document and record any
verified textbook reference beneath the heading.

## Question layout

- Separate consecutive questions with an empty line in the `.tex` source and
  approximately one blank line of vertical space in the compiled document.
- Write the assignment number literally in every heading, such as
  `\subsection*{Question 3.1: Closed-form solution}`. Do not rely only on
  LaTeX's automatic section counters.
- For a question answerable in the report, include its exact prompt beneath
  the heading and a blank `solution` environment. Define that environment in
  the preamble with a blue `Solution.` label:

  ```tex
  \newenvironment{solution}
    {\par\medskip\noindent\textcolor{blue!60!black}{\textbf{Solution.}}\par}
    {\par\medskip}
  ```

  Place an empty solution environment immediately after the full question, with
  its opening and closing commands on consecutive lines:

  ```tex
  \begin{solution}
  \end{solution}
  ```

  Leave the environment empty unless the user asks for an answer. Preserve
  existing answers when updating a report.
- For a code-only question, include its literal-numbered heading with
  `(in code)`, for example `\subsection*{Question 3.2 (in code)}`, followed by
  its exact full prompt and necessary implementation context. Omit the solution
  environment because the answer belongs in code.
- Omit unrelated administrative material, but retain shared problem setup and
  requirements needed to attempt the questions, including code questions.
- Keep the document concise: include no summaries, filler instructions, or
  extra prose outside the necessary prompts, headings, figures, textbook references, and answers.

## Final response

End the Codex response with a sentence beginning `WARNING:` that states exactly
what, if anything, was omitted from the report. If nothing was omitted, write
`WARNING: Nothing was omitted from the included assignment questions.`

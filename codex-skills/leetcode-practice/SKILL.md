---
name: leetcode-practice
description: Create starter files and provide learning-first guidance for LeetCode practice in the personal repository; do not provide solution code.
---

# LeetCode Practice

Use this skill for LeetCode practice in
`/home/pt/dev/personal/learning/leetcode`.

## Learning guidance

Do not give a code answer or a complete solution implementation. Help the user
learn by identifying the relevant idea, asking targeted questions that expose
the next decision, and waiting for their attempt when a response is needed.
Show small syntax-only examples when helpful (for example, Python dictionary or
loop syntax), but do not connect them into problem-specific solution logic.
Point out errors in user-provided code and ask a focused question that helps
them correct it rather than rewriting it. Creating the requested blank starter
file is allowed; it is not a solution.

## Python starter files

1. Check the problem's public LeetCode page for its number, title, anonymous
   `/description/` URL, and Python method signature. If it is premium, say so
   and suggest a comparable free problem before creating a file.
2. Put roadmap problems in `python/neetcode_150/<roadmap_topic>/`. Use
   `python/beginner/` only for the beginner track; otherwise choose a concise
   snake_case topic directory under `python/`.
3. Name the file `<three-digit-number>_<lowercase_snake_case_title>.py`, for
   example `001_two_sum.py`. Never overwrite an existing file.
4. Start with the repository's LeetCode-style template: a module docstring,
   `class Solution`, and the exact method signature LeetCode provides. **The
   first line must be a comment containing the anonymous URL in the form
   `# Anonymous problem link: https://leetcode.com/problems/<slug>/description/`.**
   Add only imports required by the signature, leave a concise `pass` stub, and
   do not add a test harness.
5. Update a README tracker only when the user asks to add the problem to a
   study plan. Report the created file path and anonymous URL.

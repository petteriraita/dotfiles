---
name: form-creation
description: Complete, stage, and when authorized submit the user's real online or document-based applications and forms, including supporting documents, signatures, and a usable handoff. Not for building a form as a software feature.
---

# Form Creation and Completion

Carry the user's form through as much of the actual workflow as authorized. Read the form and its instructions, discover relevant records and connected sources, and fill supported answers rather than repeatedly asking for information the user has already supplied. Preserve their existing progress. Complete independent work while an answer, login, or external action is pending; summarize material uncertainty and the remaining work plainly.

## Answers and evidence

- Read field wording and requirements closely. Distinguish a household count from tax dependents, income from assets or loan guarantees, an account overview from a statement, historical figures from current balances, and estimates from amounts actually received. Do not infer a US filing history solely from citizenship or assume missing income is zero.
- Use the user's explicit facts and relevant existing records. When a likely answer can be inferred, explain the proposed answer and its basis instead of leaving the user with an unexplained blank. Do not present uncertain financial, legal, identity, or eligibility claims as established; preserve genuinely unknown answers and identify any consequential assumptions for the user.
- Inspect all pages and applicable document categories, including conditional requirements, before declaring the application ready. Check the actual form's upload limits: if separate categories accept one file each, use those categories appropriately and combine related pages only when needed. Distinguish an original statement, an official decision, and a browser printout. Verify file type, contents, dates, and upload selection; do not claim that selecting or staging a file proves final submission.
- Save requested documents in the natural existing folder without overwriting user work. A local sync folder is not proof of cloud upload; verify synchronization when relevant and report authentication failures. Do not transmit credentials or unnecessary sensitive records.
- For requested translations, use `document-translation`: provide faithful, clearly scoped translations alongside originals as appropriate. Keep user-facing application text concise and natural; do not insert unrequested AI, verification, draft, or internal-workflow commentary into documents. Never falsely claim certification or alter the source's meaning.

## Browser, handoff, and state

Use an available service connector when it supports the work; for authenticated web downloads or saved logins, use `browser-download` and its profile and MFA rules. Inspect and navigate the actual form in a separate browser context. For phone MFA, notify the user when approval is requested and supply the service's comparison identifier when available. Keep the same session alive, wait for navigation to settle, and recover transient navigation errors without unnecessarily restarting sign-in. Never ask the user to disclose passwords or one-time codes.

Determine whether the site offers save-and-resume before promising a handoff. If it does not, preserve the actual session for the user or provide a tested, private local draft and a way to restore it into the real form. A new tab or copied URL does not necessarily preserve unsaved answers. Do not close or take over the user's ordinary browser; make it clear whether a separate window, attachment uploads, and signature will survive reopening. Prefer one working draft and one clear handoff over accumulating competing windows and versions.

When saving a dynamic or multi-page form, never overwrite stored values merely because controls are unmounted or absent from the current page. Preserve user edits and distinguish a missing control from an explicitly cleared value. Test restoring data across page changes and reloads, including the selected documents. Do not copy or persist browser cookies, authentication tokens, or credentials as part of a form draft.

## Signature and submission

If the user authorizes placing their signature, use their existing signature only when it can be identified as theirs and the form supports it; verify that the signature field actually contains it. Preserve the user's ability to review the completed application. Do not invent signatures or claim the form is signed when it is not.

Respect the user's stated submission intent: prepare a reviewable result first, and submit when they explicitly request it or give the agreed approval. Avoid repeated confirmation once authorization is clear. A brief response such as `good` can authorize submission when the agent explicitly offered it as the approval instruction. If the user says they already sent it, or submission status is ambiguous, check for a confirmation or receipt before taking another submission action. Never retry an uncertain submission blindly.

After submitting, verify the result using the site's confirmation or an actual receipt; distinguish receipt from approval. Update an existing relevant note when the user requested tracking or when it is needed to prevent duplicate work. If access or submission fails, report exactly what was completed, what remains, and the simplest next step. Keep the final response brief and make the user's remaining action concrete.

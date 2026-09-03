# Delta Spec: interactive-approval-loop

## ADDED Requirements

### Requirement: interactive-approval-loop/telegram-approval-buttons — Telegram Action Buttons
The Telegram notification system MUST provide interactive action buttons for each generated publication draft, allowing the author to approve direct publishing or reject with feedback.

#### Scenario: Draft delivery with action buttons
- GIVEN a generated publication draft with post text and carousel
- WHEN the draft package is delivered to Telegram
- THEN the message includes inline buttons for [✅ Publicar en LinkedIn] and [❌ Ajustar / Feedback]
- AND the draft state is cached in memory associated with the chat.

### Requirement: interactive-approval-loop/feedback-refinement-loop — Iterative Refinement via User Feedback
When an author clicks [❌ Ajustar / Feedback], the system MUST capture the author's follow-up feedback message and execute an automated LLM refinement pass.

#### Scenario: Author provides revision notes
- GIVEN a draft in awaiting-feedback state
- WHEN the author sends a text message describing desired modifications
- THEN the system invokes Claude Sonnet 4.5 with the original post and author feedback
- AND applies Anti-AI QC and emoji density checks to the refined post
- AND re-sends the updated draft to Telegram with new action buttons.

### Requirement: interactive-approval-loop/automated-linkedin-dispatch — Automated Publication Dispatch
When an author clicks [✅ Publicar en LinkedIn], the system MUST dispatch the publication package to LinkedIn via the active publishing backend.

#### Scenario: Author confirms publication
- GIVEN a draft presented in Telegram with action buttons
- WHEN the author clicks [✅ Publicar en LinkedIn]
- THEN BackendSelector.publish() is executed with the draft text and media URLs
- AND a confirmation message with the publication ID or status is updated in Telegram.

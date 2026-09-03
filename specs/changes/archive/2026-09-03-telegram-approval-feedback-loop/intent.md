# Intent: telegram-approval-feedback-loop

## Context
AutoLinkedInPost generates high-authority engineering posts, 4:5 native carousels, and visual assets, and now has direct publishing integrations via Publora and Pixfaro. Currently, the Telegram bot only delivers drafts as plain text and documents, requiring either manual copy-pasting or running scripts without an interactive feedback channel. The author wants an interactive human-in-the-loop approval workflow directly within Telegram that allows approving automated publication or rejecting with natural language feedback for iterative LLM refinement before anything is published to LinkedIn.

## Desired Outcome
When a post draft (with carousel and optional illustration) is prepared, the Telegram bot presents the publication package accompanied by inline action buttons: [✅ Publicar en LinkedIn] and [❌ Ajustar / Feedback]. Tapping [✅ Publicar] immediately dispatches the post to LinkedIn via the Publora API without further human friction. Tapping [❌ Ajustar] prompts the user for specific revision notes, feeds those notes back to Claude Sonnet 4.5 to re-craft the draft, and re-presents the refined package with approval buttons until the user is 100% satisfied.

## Scope
### In Scope
- Interactive inline buttons [✅ Publicar en LinkedIn] and [❌ Ajustar / Feedback] in Telegram messages.
- State machine in ot.py tracking active draft context and awaiting-feedback states per chat.
- Feedback refinement function in src/post_generator.py taking the original draft and user notes to produce an updated version through Claude Sonnet 4.5.
- Direct automated publication call via BackendSelector upon approval.
- Confirmation card and error handling in Telegram.

### Out of Scope
- Modifying third-party LinkedIn APIs or bypassing LinkedIn terms.
- Changing unprompted scheduled cron jobs without Telegram authorization.

## Key Decisions
- State persistence per chat stored in memory in ot.py (consistent with existing USER_REPOS_CACHE).
- Refinement prompt preserves 1st-person singular voice, 2026 hook formulas, and 2-line paragraph limits.
- Anti-slop Humanizer QC and emoji density checks run automatically on every refined draft.
- Publishing uses BackendSelector.publish() (Publora API).

## Success Criteria
- [ ] User receives the complete draft package with [✅ Publicar en LinkedIn] and [❌ Ajustar / Feedback] buttons in Telegram.
- [ ] Clicking [✅ Publicar] executes BackendSelector.publish() and reports post ID in Telegram.
- [ ] Clicking [❌ Ajustar] prompts for feedback and captures next user message.
- [ ] Refinement loop incorporates user notes and re-renders approval card.
- [ ] 100% automated test coverage with strict TDD.

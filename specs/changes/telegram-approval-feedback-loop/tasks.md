# Tasks: telegram-approval-feedback-loop

## Review Workload Forecast
Estimated changed lines: 250-400
Estimated product files: 3-5
Target budget: 800 lines, 15 files
Hard limit: 1000 lines, 25 files
Budget risk: Low
Independent slices possible: No
Shared production files across slices: No
Forecast basis: brief intent and focused exploration

## Delivery Plan
Strategy: single-pr
Model: whole
PR mode: draft
PR creation point: final verify only
Current delivery unit: whole

### Whole Delivery
Planned branch/base: sdd/telegram-approval-feedback-loop -> main
Scope: Interactive Telegram approval buttons, feedback refinement loop, and automated LinkedIn publishing dispatch

## Slice: whole — Interactive Telegram Approval & Feedback Loop

### Phase 1: Interactive Telegram Action Buttons & State Management
- [x] 1.1 Implement Telegram inline keyboard with publish and feedback actions
  - [x] 1.1.a Establish safety net preserving existing Telegram delivery
  - [x] 1.1.b Author failing test for approval buttons and callback payload format
  - [x] 1.1.c Implement approval keyboard builder in src/telegram_notifier.py
  - [x] 1.1.d Triangulate callback data encoding and state caching
  - [x] 1.1.e Refactor keyboard formatting for mobile Telegram screens

- [x] 1.2 Implement chat-level draft cache and callback routing in bot.py
  - [x] 1.2.a Establish safety net verifying existing /menu and callback queries
  - [x] 1.2.b Author failing test for callback_query handling of publish and feedback
  - [x] 1.2.c Implement callback handlers and awaiting_feedback state in bot.py
  - [x] 1.2.d Triangulate state transition from presented to awaiting_feedback
  - [x] 1.2.e Refactor callback handler into dedicated helper

### Phase 2: User Feedback Refinement Engine
- [x] 2.1 Implement refine_post_with_feedback in src/post_generator.py
  - [x] 2.1.a Establish safety net for existing post generation
  - [x] 2.1.b Author failing test for prompt construction with author feedback
  - [x] 2.1.c Implement refine_post_with_feedback invoking LLM with feedback instructions
  - [x] 2.1.d Triangulate refinement with Anti-AI QC and emoji density checks
  - [x] 2.1.e Refactor refinement prompt structure and error handling

- [x] 2.2 Wire interactive feedback message receiver in bot.py
  - [x] 2.2.a Establish safety net verifying regular command routing
  - [x] 2.2.b Author failing test for processing user message during awaiting_feedback state
  - [x] 2.2.c Implement feedback message interceptor and re-delivery in bot.py
  - [x] 2.2.d Triangulate multi-round feedback iterations
  - [x] 2.2.e Refactor state cleanup and user cancellation option

### Phase 3: Automated LinkedIn Publication on Approval
- [x] 3.1 Implement automated publication execution on approval callback
  - [x] 3.1.a Establish safety net verifying BackendSelector draft mode
  - [x] 3.1.b Author failing test for executing BackendSelector.publish upon approval
  - [x] 3.1.c Implement live publication dispatch and Telegram confirmation in bot.py
  - [x] 3.1.d Triangulate error handling when Publora returns API failure
  - [x] 3.1.e Refactor Telegram status card presentation

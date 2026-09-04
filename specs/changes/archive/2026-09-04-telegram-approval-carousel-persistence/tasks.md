# Tasks: telegram-approval-carousel-persistence

## Review Workload Forecast
Estimated changed lines: 250-400
Estimated product files: 4-6
Target budget: 800 lines, 15 files
Hard limit: 1000 lines, 25 files
Budget risk: Low
Independent slices possible: No
Shared production files across slices: No
Forecast basis: brief intent, delta spec, and focused exploration of bot.py, publora.py, backends.py, main.py, and workflows

## Delivery Plan
Strategy: single-pr
Model: whole
PR mode: draft
PR creation point: final verify only
Current delivery unit: whole

### Whole Delivery
Planned branch/base: sdd/telegram-approval-carousel-persistence -> main
Scope: Pre-creation of carousel drafts in Publora, callback data binding with postGroupId, direct draft scheduling dispatch in bot.py, legacy fallback, CI secrets and matrix checks.

## Slice: whole — Telegram Approval Carousel Persistence

### Phase 1: Publora Client & Backend Draft Lifecycle
- [x] 1.1 Extend PubloraClient with publish_draft / update-post method
  - [x] 1.1.a Establish safety net verifying existing PubloraClient create_post behavior
  - [x] 1.1.b Author failing test for PubloraClient.publish_draft making PUT /update-post/{id}
  - [x] 1.1.c Implement publish_draft in src/linkedin/clients/publora.py
  - [x] 1.1.d Triangulate publish_draft with custom scheduled_at vs default now+1min
  - [x] 1.1.e Refactor header authorization and error handling for update-post calls

- [x] 1.2 Extend BackendSelector with create_draft and publish_draft dispatchers
  - [x] 1.2.a Establish safety net for existing BackendSelector.publish
  - [x] 1.2.b Author failing test for BackendSelector.create_draft and BackendSelector.publish_draft
  - [x] 1.2.c Implement create_draft and publish_draft in src/linkedin/backends.py
  - [x] 1.2.d Triangulate BackendSelector behavior in draft/mock mode when Publora credentials absent
  - [x] 1.2.e Refactor BackendSelector method signatures and type annotations

### Phase 2: Draft Pre-Creation & Callback Data Binding
- [x] 2.1 Update build_approval_keyboard and Telegram notification with postGroupId
  - [x] 2.1.a Establish safety net verifying build_approval_keyboard formatting
  - [x] 2.1.b Author failing test for build_approval_keyboard preserving full draft_id (up to 55 chars) under 64 bytes
  - [x] 2.1.c Update build_approval_keyboard in src/telegram_notifier.py to prevent truncating UUID/CUID draft IDs
  - [x] 2.1.d Triangulate callback data byte length with 36-character UUIDs and 24-character IDs
  - [x] 2.1.e Refactor approval button generation to cleanly pass draft_id from draft dictionaries

- [x] 2.2 Pre-create Publora drafts with carousels in main.py and bot.py showcase
  - [x] 2.2.a Establish safety net for main.py execution and bot.py showcase generation
  - [x] 2.2.b Author failing test for main.py calling BackendSelector.create_draft when carousels are compiled
  - [x] 2.2.c Integrate draft pre-creation in main.py and bot.py handle_callback_query (sc/sc_en)
  - [x] 2.2.d Triangulate graceful degradation when draft pre-creation fails (dry-run, network timeout)
  - [x] 2.2.e Refactor draft metadata aggregation and logging

### Phase 3: Bot Approval Dispatch, Robust Fallback & CI Workflow
- [x] 3.1 Implement direct draft publishing and legacy fallback in bot.py approval handler
  - [x] 3.1.a Establish safety net for bot.py handle_approval_callback
  - [x] 3.1.b Author failing test for handle_approval_callback dispatching publish_draft when target_id is a postGroupId
  - [x] 3.1.c Update handle_approval_callback in bot.py to publish existing draft directly via BackendSelector
  - [x] 3.1.d Triangulate fallback path when target_id is a legacy repo name or draft publishing raises 404
  - [x] 3.1.e Refactor callback response messages to distinguish draft publishing with carousel vs fallback

- [x] 3.2 Update GitHub Actions daily workflow with Publora secrets and CI safety checks
  - [x] 3.2.a Establish safety net validating .github/workflows/ci.yml and daily_linkedin_post.yml syntax
  - [x] 3.2.b Author failing test for workflow configuration requiring PUBLORA_API_KEY and LINKEDIN_PLATFORM_ID
  - [x] 3.2.c Update .github/workflows/daily_linkedin_post.yml to inject PUBLORA_API_KEY and LINKEDIN_PLATFORM_ID
  - [x] 3.2.d Triangulate test suite execution with ruff linting and python 3.11 / 3.12 compatibility
  - [x] 3.2.e Refactor CI configuration documentation in README.md and docs/scheduling.md

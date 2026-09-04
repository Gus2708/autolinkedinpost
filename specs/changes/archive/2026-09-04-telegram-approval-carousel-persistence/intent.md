# Intent: telegram-approval-carousel-persistence

## Context
AutoLinkedInPost generates daily automated drafts and on-demand project showcases featuring high-authority LinkedIn copy, first-comment strategies, and native 4:5 multipage PDF carousels. Currently, daily drafts generated in GitHub Actions (or local CLI runners) are sent to Telegram with interactive approval buttons: `[🚀 Publicar en LinkedIn]` and `[✏️ Ajustar / Feedback]`.

When the user taps `[🚀 Publicar en LinkedIn]`, the callback is received by `bot.py` hosted on Render. Because the GitHub Actions runner has already terminated and Render operates on an ephemeral filesystem, `USER_DRAFTS_CACHE` on Render is empty and `data/latest_carousel_{chat_id}.pdf` does not exist on Render's disk. Consequently, `bot.py` falls back to `BackendSelector().publish(text, pdf_bytes=None)`, which posts text only to LinkedIn, discarding the entire generated PDF carousel.

## Desired Outcome
When draft generation occurs (both in the daily GitHub Actions cron and in interactive bot showcases), drafts with carousels are pre-created directly in the Publora API with `draft: true` and the PDF carousel uploaded to S3 via the `/get-upload-url` and `/complete-media` workflow. Publora persists the draft and returns a `postGroupId`.

The Telegram approval button encodes this reference: `publi_{postGroupId}` (remaining strictly under Telegram's 64-byte callback_data limit). When the user clicks `[🚀 Publicar en LinkedIn]`, `bot.py` directly executes Publora's `PUT /update-post/{postGroupId}` setting `status: "scheduled"` with the immediate execution time. Zero ephemeral file transfer is required between GitHub Actions and Render, guaranteeing that LinkedIn publishes the complete post accompanied by the PDF carousel.

## Scope
### In Scope
- **Publora Draft Pre-creation**: In `main.py` and `bot.py`, pre-create posts in Publora as drafts (`draft: true`) with PDF carousel uploaded to S3 when Publora credentials are present.
- **Client & Backend API Extensions**: Add `publish_draft` to `PubloraClient` and dispatcher methods `create_draft` and `publish_draft` to `BackendSelector`.
- **Telegram Callback Binding**: Update `build_approval_keyboard` in `src/telegram_notifier.py` to bind `draft_id` (`publi_{postGroupId}`) without truncation and strictly under the 64-byte limit.
- **Bot Publishing Handler**: Update `handle_approval_callback` in `bot.py` to identify draft IDs and trigger direct draft publication via `BackendSelector.publish_draft`.
- **Robust Fallback**: If an older or plain repo callback arrives (`publi_user_repo`), or if draft publishing fails, gracefully fall back to existing text/cache publishing without crashing.
- **CI & Workflow Secrets**: Update `.github/workflows/daily_linkedin_post.yml` to inject `PUBLORA_API_KEY` and `LINKEDIN_PLATFORM_ID`, and ensure linting/matrix tests in `.github/workflows/ci.yml`.

### Out of Scope
- Inter-server file streaming or FTP/SCP storage of ephemeral PDF files between GitHub Actions and Render.
- Altering Publora's external API contracts or LinkedIn platform constraints.
- Modifying non-Publora backends (Pixfaro, Tier 0 local draft) beyond keeping existing behavior intact.

## Key Decisions
- **Publora as Single Source of Truth**: The draft and its S3-hosted PDF binary live in Publora's persistent cloud storage. No ephemeral disk or shared network drive is required between runners and the bot.
- **Callback Data Optimization**: Telegram limits `callback_data` to 64 bytes. `publi_` (6 chars) + `postGroupId` (typically 24–36 chars) totals 30–42 bytes, comfortably fitting without truncation. `build_approval_keyboard` will preserve up to 55 characters for `draft_id`.
- **Stateless Verification on Render**: Render does not need to know the repo context or maintain cache across restarts to publish the approved draft. It only needs the `postGroupId` from the callback.
- **Defensive Fallback**: If `target_id` does not match a known draft or API update fails, the handler falls back to extracting post text from the Telegram message and attempting direct publication.

## Technical Approach
1. **PubloraClient Enhancements (`src/linkedin/clients/publora.py`)**:
   - Implement `publish_draft(post_group_id: str, scheduled_at: Optional[str] = None) -> Dict[str, Any]` sending `PUT /update-post/{post_group_id}` with `status: "scheduled"` and `scheduledTime: target_time`.
2. **BackendSelector Enhancements (`src/linkedin/backends.py`)**:
   - Add `create_draft(text, pdf_bytes, **kwargs)` delegating to `publora_client.create_post(..., draft=True)`.
   - Add `publish_draft(draft_id, **kwargs)` delegating to `publora_client.publish_draft(draft_id, ...)`.
3. **Telegram Keyboard Binding (`src/telegram_notifier.py`)**:
   - Update `build_approval_keyboard(repo_name, draft_id=None)`: if `draft_id` is supplied, use `f"publi_{draft_id[:55]}"` to avoid truncating 36-char UUIDs while strictly respecting Telegram's 64-byte limit.
4. **Draft Pre-Creation Flow**:
   - In `main.py`, after carousel compilation and before Telegram notification, call `selector.create_draft(...)` when Publora is active, setting `draft["draft_id"] = res["id"]`.
   - In `bot.py` showcase generation (`sc:` / `sc_en:`), pre-create draft in Publora and pass `draft_id` to `build_approval_keyboard`.
5. **Approval Callback Execution (`bot.py`)**:
   - In `handle_approval_callback`: If `target_id` represents a draft ID or Publora is active, call `selector.publish_draft(target_id)`. If successful, acknowledge to Telegram with post ID and carousel confirmation. If it fails or is a legacy repo target, fall back to current `selector.publish(text=post_text, pdf_bytes=pdf_bytes)`.
6. **Workflow Configuration (`.github/workflows/daily_linkedin_post.yml`)**:
   - Add `PUBLORA_API_KEY: ${{ secrets.PUBLORA_API_KEY }}` and `LINKEDIN_PLATFORM_ID: ${{ secrets.LINKEDIN_PLATFORM_ID }}` to step environment variables.

## Success Criteria
- [ ] `PubloraClient.publish_draft` schedules an existing draft with Publora API via `PUT /update-post/{id}`.
- [ ] `BackendSelector.create_draft` and `BackendSelector.publish_draft` dispatch correctly.
- [ ] `build_approval_keyboard` safely accepts 36-char UUIDs without truncation while guaranteeing <= 64 bytes.
- [ ] `main.py` and `bot.py` showcase generation pre-create Publora drafts when carousels are compiled and Publora is configured.
- [ ] Clicking `[🚀 Publicar en LinkedIn]` in Telegram schedules the pre-created draft in Publora containing the carousel PDF, even when Render's local cache is empty.
- [ ] Legacy callbacks without draft IDs gracefully execute fallback publishing without crashing.
- [ ] GitHub Actions daily workflow contains `PUBLORA_API_KEY` and `LINKEDIN_PLATFORM_ID`.
- [ ] 100% automated test coverage with strict TDD and passing ruff checks.

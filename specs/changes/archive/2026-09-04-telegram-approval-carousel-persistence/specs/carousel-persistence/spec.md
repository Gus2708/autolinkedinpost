# Delta Spec: carousel-persistence

## ADDED Requirements

### Requirement: carousel-persistence/publora-draft-precreation — Publora Pre-Creation of Carousel Drafts
The system MUST pre-create posts in Publora as drafts with the PDF carousel uploaded to S3 and media completed before sending notifications to Telegram when Publora is configured.

#### Scenario: Draft pre-creation with PDF carousel in cron/CLI
- GIVEN a generated publication post and a compiled native carousel PDF
- WHEN the active publishing backend is Publora
- THEN the system invokes Publora with draft: true and pdf_bytes
- AND uploads the PDF to S3 via get-upload-url and executes complete-media
- AND retains the returned postGroupId for Telegram callback routing.

#### Scenario: Draft pre-creation with PDF carousel in interactive bot showcase
- GIVEN an interactive project showcase requested via Telegram bot
- WHEN the showcase post and carousel PDF are compiled
- AND Publora is the active backend
- THEN the draft is pre-created in Publora as a draft
- AND its postGroupId is bound to the interactive approval buttons.

### Requirement: carousel-persistence/telegram-draft-callback-binding — Telegram Approval Callback Binding
The Telegram notification system MUST bind the Publora draft ID into the approval callback data, respecting Telegram's 64-byte limit.

#### Scenario: Approval keyboard construction with draft ID
- GIVEN a draft with a resolved postGroupId
- WHEN build_approval_keyboard is invoked with draft_id=postGroupId
- THEN the callback data for [🚀 Publicar en LinkedIn] is formatted as publi_{postGroupId}
- AND the total callback_data byte length does not exceed 64 bytes.

### Requirement: carousel-persistence/automated-draft-publication-dispatch — Direct Draft Publication Dispatch
When the user clicks [🚀 Publicar en LinkedIn] with a draft ID callback, the bot MUST publish the pre-created draft directly in Publora by updating its status to scheduled.

#### Scenario: Direct draft publishing on approval callback
- GIVEN a Telegram approval callback with action publi and target_id matching a Publora postGroupId
- WHEN the user clicks [🚀 Publicar en LinkedIn]
- THEN bot.py invokes BackendSelector.publish_draft(post_group_id)
- AND Publora executes PUT /update-post/{post_group_id} with status=scheduled and scheduledTime at current time + 1 minute
- AND LinkedIn publishes the post containing the pre-attached carousel PDF without transferring binary files across environments
- AND a confirmation message is sent to Telegram with the publication ID.

### Requirement: carousel-persistence/legacy-callback-fallback — Robust Fallback for Legacy or Non-Draft Callbacks
The system MUST handle legacy callbacks without draft IDs or when draft publishing fails, preserving backward compatibility.

#### Scenario: Legacy callback without draft ID received
- GIVEN a Telegram callback data formatted with a repository name rather than a draft ID (e.g. publi_{repo_name})
- WHEN the user clicks [🚀 Publicar en LinkedIn]
- THEN the system detects that the target_id is not a valid draft ID
- AND attempts fallback resolution using in-memory cache or local latest_carousel file if present
- AND executes standard BackendSelector.publish with available content and appropriate user notification.

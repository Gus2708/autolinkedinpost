# Spec: linkedin-integration-engine

## Domain Overview
Domain behavior synchronized from change artifacts.

## Requirements

### Requirement: linkedin-integration-engine/url-parsing — LinkedIn URL and URN Extraction
The system MUST extract the activity URN and optional comment identifier from LinkedIn post and comment URLs.

#### Scenario: Parse valid post and comment URLs
- GIVEN a valid LinkedIn post or comment URL string
- WHEN \parse_linkedin_url\ is called
- THEN it returns a dictionary containing \post_urn\ and optional \comment_id\.

#### Scenario: Handle invalid URL input
- GIVEN an invalid or non-LinkedIn URL string
- WHEN \parse_linkedin_url\ is called
- THEN it raises ValueError or returns None without crashing the caller.

### Requirement: linkedin-integration-engine/backend-publishing — Multi-Backend Publishing Adapter
The system MUST support publishing via Publora API with automatic fallback to Tier 0 Draft mode when credentials are missing.

#### Scenario: Auto-publish when Publora credentials are configured
- GIVEN valid \PUBLORA_API_KEY\ and \LINKEDIN_PLATFORM_ID\ in the environment
- WHEN a publish request is submitted to the backend selector
- THEN the Publora client sends the post payload via HTTP and returns a success response with post ID.

#### Scenario: Tier 0 fallback when credentials are absent
- GIVEN unset or empty publishing API keys
- WHEN a publish request is submitted
- THEN the backend selector activates Tier 0 (Draft mode) and returns a formatted copy-paste text block.

### Requirement: linkedin-integration-engine/approval-gate — Human Approval Gate
The system MUST require explicit user confirmation before executing any network publication call.

#### Scenario: Block publication without explicit confirmation
- GIVEN a drafted post ready for publication
- WHEN approval has not been confirmed
- THEN the approval gate returns status pending and prevents dispatch to remote APIs.

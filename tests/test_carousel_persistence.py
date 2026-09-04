"""Tests for carousel persistence: Publora draft pre-creation in main.py and bot.py showcase."""
from unittest.mock import MagicMock
import pytest

from src.linkedin.backends import BackendSelector


def test_main_precreates_publora_drafts_when_active(monkeypatch):
    import main
    from main import main as run_main

    # Mock sys.argv
    monkeypatch.setattr("sys.argv", ["main.py", "--mock", "--lang", "es"])
    monkeypatch.setattr("os.environ", {
        "PUBLORA_API_KEY": "fake_key",
        "LINKEDIN_PLATFORM_ID": "plat_123",
        "TELEGRAM_BOT_TOKEN": "bot_token",
        "TELEGRAM_CHAT_ID": "chat_123",
    })

    # Mock validate_provider_credentials
    monkeypatch.setattr("main.validate_provider_credentials", lambda *a, **k: (True, None))

    # Mock post generation
    mock_drafts = [
        {
            "repo_name": "empresa/core-api",
            "post": "Post content for core-api",
            "first_comment": "First comment",
            "carousel_script": "Slide 1...",
        }
    ]
    monkeypatch.setattr("main.generate_posts_by_project", lambda *a, **k: mock_drafts)

    # Mock carousel rendering
    monkeypatch.setattr(
        "main.generate_native_carousel_pdf",
        lambda *a, **k: (b"%PDF-carousel", None, None, {"visual_audited": True, "overall_score": 4.9}),
    )

    # Mock BackendSelector.create_draft
    mock_create_draft = MagicMock(return_value={"id": "post_grp_abc123", "status": "draft", "backend": "publora"})
    monkeypatch.setattr(BackendSelector, "create_draft", mock_create_draft)

    # Mock send_telegram_project_drafts
    mock_send_telegram = MagicMock(return_value=True)
    monkeypatch.setattr("main.send_telegram_project_drafts", mock_send_telegram)

    run_main()

    # Verify BackendSelector.create_draft was called with post content and pdf_bytes
    assert mock_create_draft.call_count == 1
    call_kwargs = mock_create_draft.call_args.kwargs
    assert call_kwargs["text"] == "Post content for core-api"
    assert call_kwargs["pdf_bytes"] == b"%PDF-carousel"

    # Verify send_telegram_project_drafts received draft with draft_id populated
    assert mock_send_telegram.call_count == 1
    sent_drafts = mock_send_telegram.call_args.kwargs["drafts"]
    assert sent_drafts[0].get("draft_id") == "post_grp_abc123"


def test_bot_showcase_precreates_publora_draft(monkeypatch):
    import bot
    from bot import handle_callback_query, USER_REPOS_CACHE, USER_DRAFTS_CACHE

    USER_REPOS_CACHE[12345] = [{"full_name": "owner/awesome-repo", "name": "awesome-repo"}]
    USER_DRAFTS_CACHE.clear()

    monkeypatch.setattr("os.environ", {
        "PUBLORA_API_KEY": "fake_key",
        "LINKEDIN_PLATFORM_ID": "plat_123",
    })

    # Mock telegram_api_request
    monkeypatch.setattr("bot.telegram_api_request", lambda *a, **k: {"ok": True})

    # Mock deep context
    monkeypatch.setattr("bot.fetch_repository_deep_context", lambda *a, **k: {"readme": "Clean code"})

    # Mock post generation
    monkeypatch.setattr(
        "bot.generate_project_showcase_post",
        lambda *a, **k: {
            "post": "Showcase post for awesome-repo",
            "first_comment": "First comment",
            "carousel_script": "Slide 1...",
            "quality_score": 4.8,
            "used_model": "claude-sonnet",
        },
    )

    # Mock carousel renderer
    monkeypatch.setattr(
        "bot.generate_native_carousel_pdf",
        lambda *a, **k: (b"%PDF-bot-carousel", None, None, {"visual_audited": True, "overall_score": 5.0}),
    )

    # Mock BackendSelector.create_draft
    mock_create_draft = MagicMock(return_value={"id": "bot_draft_456", "status": "draft", "backend": "publora"})
    monkeypatch.setattr(BackendSelector, "create_draft", mock_create_draft)

    # Mock send_single_project_draft
    mock_send_draft = MagicMock(return_value=True)
    monkeypatch.setattr("bot.send_single_project_draft", mock_send_draft)

    cb_query = {
        "id": "cb_999",
        "data": "sc:0",
        "message": {"chat": {"id": 12345}, "message_id": 42},
    }

    handle_callback_query("dummy_token", cb_query)

    # Verify BackendSelector.create_draft called
    assert mock_create_draft.call_count == 1
    call_kwargs = mock_create_draft.call_args.kwargs
    assert call_kwargs["text"] == "Showcase post for awesome-repo"
    assert call_kwargs["pdf_bytes"] == b"%PDF-bot-carousel"

    # Verify draft saved in cache contains draft_id
    assert USER_DRAFTS_CACHE[12345].get("draft_id") == "bot_draft_456"

    # Verify send_single_project_draft received reply_markup with publi_bot_draft_456
    assert mock_send_draft.call_count == 1
    reply_markup = mock_send_draft.call_args.kwargs["reply_markup"]
    callback_datas = [
        btn["callback_data"]
        for row in reply_markup["inline_keyboard"]
        for btn in row
    ]
    assert "publi_draft_bot_draft_456" in callback_datas


def test_main_dry_run_skips_publora_draft_creation(monkeypatch):
    from main import main as run_main

    monkeypatch.setattr("sys.argv", ["main.py", "--mock", "--dry-run", "--lang", "es"])
    monkeypatch.setattr("os.environ", {
        "PUBLORA_API_KEY": "fake_key",
        "LINKEDIN_PLATFORM_ID": "plat_123",
    })
    monkeypatch.setattr("main.validate_provider_credentials", lambda *a, **k: (True, None))
    mock_drafts = [{"repo_name": "org/repo", "post": "Test post", "carousel_script": "Slide"}]
    monkeypatch.setattr("main.generate_posts_by_project", lambda *a, **k: mock_drafts)
    monkeypatch.setattr("main.generate_native_carousel_pdf", lambda *a, **k: (b"%PDF", None, None, {}))

    mock_create_draft = MagicMock()
    monkeypatch.setattr(BackendSelector, "create_draft", mock_create_draft)

    run_main()

    # Dry-run MUST NOT create drafts in external API
    assert mock_create_draft.call_count == 0


def test_main_graceful_degradation_on_publora_error(monkeypatch):
    from main import main as run_main

    monkeypatch.setattr("sys.argv", ["main.py", "--mock", "--lang", "es"])
    monkeypatch.setattr("os.environ", {
        "PUBLORA_API_KEY": "fake_key",
        "LINKEDIN_PLATFORM_ID": "plat_123",
        "TELEGRAM_BOT_TOKEN": "bot_token",
        "TELEGRAM_CHAT_ID": "chat_123",
    })
    monkeypatch.setattr("main.validate_provider_credentials", lambda *a, **k: (True, None))
    mock_drafts = [{"repo_name": "org/repo", "post": "Test post", "carousel_script": "Slide"}]
    monkeypatch.setattr("main.generate_posts_by_project", lambda *a, **k: mock_drafts)
    monkeypatch.setattr("main.generate_native_carousel_pdf", lambda *a, **k: (b"%PDF", None, None, {}))

    # Simulate network timeout/failure in create_draft
    mock_create_draft = MagicMock(side_effect=Exception("Publora S3 Timeout"))
    monkeypatch.setattr(BackendSelector, "create_draft", mock_create_draft)

    mock_send_telegram = MagicMock(return_value=True)
    monkeypatch.setattr("main.send_telegram_project_drafts", mock_send_telegram)

    # Should not raise exception
    run_main()

    assert mock_create_draft.call_count == 1
    assert mock_send_telegram.call_count == 1
    sent_drafts = mock_send_telegram.call_args.kwargs["drafts"]
    # draft_id is not set when create_draft failed
    assert sent_drafts[0].get("draft_id") is None


def test_bot_showcase_graceful_degradation_on_publora_error(monkeypatch):
    from bot import handle_callback_query, USER_REPOS_CACHE, USER_DRAFTS_CACHE

    USER_REPOS_CACHE[99999] = [{"full_name": "owner/failing-repo", "name": "failing-repo"}]
    USER_DRAFTS_CACHE.clear()

    monkeypatch.setattr("os.environ", {
        "PUBLORA_API_KEY": "fake_key",
        "LINKEDIN_PLATFORM_ID": "plat_123",
    })
    monkeypatch.setattr("bot.telegram_api_request", lambda *a, **k: {"ok": True})
    monkeypatch.setattr("bot.fetch_repository_deep_context", lambda *a, **k: {"readme": "Code"})
    monkeypatch.setattr(
        "bot.generate_project_showcase_post",
        lambda *a, **k: {"post": "Post", "carousel_script": "Slide"},
    )
    monkeypatch.setattr("bot.generate_native_carousel_pdf", lambda *a, **k: (b"%PDF", None, None, {}))

    mock_create_draft = MagicMock(side_effect=Exception("Publora 500 error"))
    monkeypatch.setattr(BackendSelector, "create_draft", mock_create_draft)

    mock_send_draft = MagicMock(return_value=True)
    monkeypatch.setattr("bot.send_single_project_draft", mock_send_draft)

    cb_query = {
        "id": "cb_fail",
        "data": "sc:0",
        "message": {"chat": {"id": 99999}, "message_id": 10},
    }

    handle_callback_query("dummy_token", cb_query)

    assert mock_create_draft.call_count == 1
    # Cached draft has None for draft_id
    assert USER_DRAFTS_CACHE[99999].get("draft_id") is None
    # Reply markup falls back to repo name
    reply_markup = mock_send_draft.call_args.kwargs["reply_markup"]
    callback_datas = [
        btn["callback_data"]
        for row in reply_markup["inline_keyboard"]
        for btn in row
    ]
    assert "publi_owner_failing-repo" in callback_datas



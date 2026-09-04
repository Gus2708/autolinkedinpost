import pytest

def test_build_approval_keyboard_structure():
    from src.telegram_notifier import build_approval_keyboard

    kb = build_approval_keyboard(repo_name='user/repo-api', draft_id='draft-1')
    assert 'inline_keyboard' in kb
    buttons = kb['inline_keyboard'][0]
    assert len(buttons) == 2
    
    pub_btn = buttons[0]
    feed_btn = buttons[1]
    assert 'Publicar' in pub_btn['text']
    assert pub_btn['callback_data'].startswith('publi_')
    assert ('Feedback' in feed_btn['text'] or 'Ajustar' in feed_btn['text'])
    assert feed_btn['callback_data'].startswith('feedb_')

def test_build_approval_keyboard_truncates_long_names_under_telegram_limit():
    from src.telegram_notifier import build_approval_keyboard

    long_repo = 'a' * 100
    kb = build_approval_keyboard(repo_name=long_repo)
    cb_pub = kb['inline_keyboard'][0][0]['callback_data']
    cb_feed = kb['inline_keyboard'][0][1]['callback_data']
    
    # Telegram limit for callback_data is 64 bytes
    assert len(cb_pub.encode('utf-8')) <= 64
    assert len(cb_feed.encode('utf-8')) <= 64
    assert cb_pub.startswith('publi_')
    assert cb_feed.startswith('feedb_')


def test_build_approval_keyboard_preserves_full_draft_id_uuid():
    from src.telegram_notifier import build_approval_keyboard

    uuid_draft_id = "12345678-1234-5678-1234-567812345678"  # 36 chars
    assert len(uuid_draft_id) == 36
    kb = build_approval_keyboard(repo_name="my/repo", draft_id=uuid_draft_id)
    cb_pub = kb["inline_keyboard"][0][0]["callback_data"]
    cb_feed = kb["inline_keyboard"][0][1]["callback_data"]

    assert cb_pub == f"publi_draft_{uuid_draft_id}"
    assert cb_feed == f"feedb_draft_{uuid_draft_id}"
    assert len(cb_pub.encode("utf-8")) <= 64
    assert len(cb_feed.encode("utf-8")) <= 64


def test_build_approval_keyboard_triangulation_ids_and_batch_send():
    from unittest.mock import patch
    from src.telegram_notifier import build_approval_keyboard, send_telegram_project_drafts

    # 24-char Mongo/CUID style ID
    cuid_id = "clh1234567890abcdef12345"  # 24 chars
    kb_24 = build_approval_keyboard("repo", draft_id=cuid_id)
    assert kb_24["inline_keyboard"][0][0]["callback_data"] == f"publi_draft_{cuid_id}"
    assert len(kb_24["inline_keyboard"][0][0]["callback_data"].encode("utf-8")) <= 64

    # 55-char exact boundary ID (already with draft_ prefix)
    boundary_id = "draft_" + ("x" * 49)  # 55 chars
    kb_55 = build_approval_keyboard("repo", draft_id=boundary_id)
    assert kb_55["inline_keyboard"][0][0]["callback_data"] == f"publi_{boundary_id}"
    assert len(kb_55["inline_keyboard"][0][0]["callback_data"].encode("utf-8")) == 61  # 6 + 55 = 61 <= 64

    # > 55 chars truncated to 55 to strictly guarantee <= 64 bytes
    long_id = "draft_" + ("y" * 80)
    kb_long = build_approval_keyboard("repo", draft_id=long_id)
    assert kb_long["inline_keyboard"][0][0]["callback_data"] == f"publi_{long_id[:55]}"
    assert len(kb_long["inline_keyboard"][0][0]["callback_data"].encode("utf-8")) <= 64

    # Verify send_telegram_project_drafts binds draft_id into keyboard
    drafts = [
        {"repo_name": "org/repo", "post": "Test post", "draft_id": "draft_abc_123"}
    ]
    with patch("src.telegram_notifier.send_single_project_draft") as mock_send:
        mock_send.return_value = True
        send_telegram_project_drafts("token", "12345", drafts)
        mock_send.assert_called_once()
        call_kwargs = mock_send.call_args.kwargs
        reply_markup = call_kwargs["reply_markup"]
        assert reply_markup["inline_keyboard"][0][0]["callback_data"] == "publi_draft_abc_123"



def test_refine_post_with_feedback_signature_and_prompt():
    from src.post_generator import refine_post_with_feedback
    from unittest.mock import patch

    original = 'Post original sobre Redis cache'
    feedback = 'Hace enfasis en latencia p99 de 60ms y quita el Redlock'

    with patch('src.post_generator.generate_llm_text') as mock_llm:
        mock_llm.return_value = ('Post refinado con p99 60ms', 'anthropic/claude-sonnet-4.5')
        res = refine_post_with_feedback(
            original_post=original,
            user_feedback=feedback,
            repo_name='user/repo-api'
        )
        assert res['post'] == 'Post refinado con p99 60ms'
        assert res['used_model'] == 'anthropic/claude-sonnet-4.5'
        prompt_arg = mock_llm.call_args.kwargs.get("prompt") or mock_llm.call_args[0][0]
        assert 'Hace enfasis en latencia p99 de 60ms' in prompt_arg
        assert 'Post original sobre Redis cache' in prompt_arg

def test_refine_post_with_feedback_runs_humanizer_qc():
    from src.post_generator import refine_post_with_feedback
    from unittest.mock import patch

    with patch('src.post_generator.generate_llm_text') as mock_llm:
        mock_llm.return_value = ('Post refinado limpio sin slop', 'anthropic/claude-sonnet-4.5')
        res = refine_post_with_feedback(
            original_post='Original',
            user_feedback='Ajustalo',
            repo_name='user/repo'
        )
        assert 'humanizer_qc' in res
        assert 'score' in res['humanizer_qc'] or 'passed' in res['humanizer_qc']

def test_handle_approval_callback_publish():
    from bot import handle_approval_callback, USER_DRAFTS_CACHE
    from unittest.mock import MagicMock, patch

    chat_id = 999
    USER_DRAFTS_CACHE[chat_id] = {
        'repo_name': 'test/repo',
        'post': 'Contenido del post para LinkedIn',
    }

    with patch('bot.BackendSelector') as mock_bs, patch('bot.telegram_api_request') as mock_tg:
        mock_instance = MagicMock()
        mock_instance.publish.return_value = {'status': 'published', 'raw': {'postGroupId': 'post-abc'}}
        mock_bs.return_value = mock_instance

        handle_approval_callback(
            bot_token='fake_token',
            chat_id=chat_id,
            callback_id='cb_1',
            action='publi',
            target_id='test_repo'
        )

        # Verify publish called with draft text and pdf_bytes
        mock_instance.publish.assert_called_once_with(text='Contenido del post para LinkedIn', pdf_bytes=None)
        # Verify telegram notification sent
        assert any('publicado' in str(call).lower() for call in mock_tg.call_args_list)


def test_handle_approval_callback_publish_with_carousel_pdf():
    from bot import handle_approval_callback, USER_DRAFTS_CACHE
    from unittest.mock import MagicMock, patch

    chat_id = 998
    dummy_pdf = b'%PDF-1.4 dummy'
    USER_DRAFTS_CACHE[chat_id] = {
        'repo_name': 'test/repo',
        'post': 'Post con carrusel',
        'pdf_bytes': dummy_pdf,
    }

    with patch('bot.BackendSelector') as mock_bs, patch('bot.telegram_api_request') as mock_tg:
        mock_instance = MagicMock()
        mock_instance.publish.return_value = {'status': 'published', 'raw': {'postGroupId': 'post-123'}}
        mock_bs.return_value = mock_instance

        handle_approval_callback(
            bot_token='fake_token',
            chat_id=chat_id,
            callback_id='cb_1b',
            action='publi',
            target_id='test_repo'
        )

        mock_instance.publish.assert_called_once_with(text='Post con carrusel', pdf_bytes=dummy_pdf)
        assert any('carrusel' in str(call).lower() for call in mock_tg.call_args_list)


def test_handle_approval_callback_dispatches_publish_draft():
    from bot import handle_approval_callback, USER_DRAFTS_CACHE
    from unittest.mock import MagicMock, patch

    chat_id = 999
    USER_DRAFTS_CACHE.pop(chat_id, None)  # Stateless Render: cache is empty

    with patch('bot.BackendSelector') as mock_bs, patch('bot.telegram_api_request') as mock_tg:
        mock_instance = MagicMock()
        mock_instance.active_backend = "publora"
        mock_instance.publish_draft.return_value = {
            'status': 'published',
            'backend': 'publora',
            'id': 'post_group_xyz',
            'raw': {'postGroupId': 'post_group_xyz'},
        }
        mock_bs.return_value = mock_instance

        handle_approval_callback(
            bot_token='fake_token',
            chat_id=chat_id,
            callback_id='cb_draft_1',
            action='publi',
            target_id='draft_post_group_xyz',
            message_text=None,
        )

        mock_instance.publish_draft.assert_called_once_with('post_group_xyz')
        mock_instance.publish.assert_not_called()
        # Verify success message sent with post ID and carousel confirmation
        sent_messages = [str(call) for call in mock_tg.call_args_list]
        assert any('post_group_xyz' in msg for msg in sent_messages)
        assert any('carrusel' in msg.lower() or 'pdf' in msg.lower() for msg in sent_messages)


def test_handle_approval_callback_draft_404_falls_back_to_publish():
    from bot import handle_approval_callback, USER_DRAFTS_CACHE
    from unittest.mock import MagicMock, patch

    chat_id = 991
    USER_DRAFTS_CACHE[chat_id] = {
        'repo_name': 'test/repo',
        'post': 'Fallback post content',
        'pdf_bytes': b'%PDF-fallback',
    }

    with patch('bot.BackendSelector') as mock_bs, patch('bot.telegram_api_request') as mock_tg:
        mock_instance = MagicMock()
        mock_instance.active_backend = "publora"
        # publish_draft fails with 404
        mock_instance.publish_draft.side_effect = Exception("HTTP 404 Not Found")
        mock_instance.publish.return_value = {
            'status': 'published',
            'backend': 'publora',
            'id': 'fallback_pub_id',
        }
        mock_bs.return_value = mock_instance

        handle_approval_callback(
            bot_token='fake_token',
            chat_id=chat_id,
            callback_id='cb_fail_1',
            action='publi',
            target_id='draft_expired_123',
            message_text=None,
        )

        # Verified publish_draft was attempted first
        mock_instance.publish_draft.assert_called_once_with('expired_123')
        # And fallback publish was executed with available content
        mock_instance.publish.assert_called_once_with(text='Fallback post content', pdf_bytes=b'%PDF-fallback')
        # Success message indicates published post ID
        sent_messages = [str(call) for call in mock_tg.call_args_list]
        assert any('fallback_pub_id' in msg for msg in sent_messages)




def test_handle_approval_callback_feedback():
    from bot import handle_approval_callback, USER_DRAFTS_CACHE, AWAITING_FEEDBACK_CACHE
    from unittest.mock import patch

    chat_id = 888
    USER_DRAFTS_CACHE[chat_id] = {
        'repo_name': 'test/repo',
        'post': 'Contenido original',
    }

    with patch('bot.telegram_api_request') as mock_tg:
        handle_approval_callback(
            bot_token='fake_token',
            chat_id=chat_id,
            callback_id='cb_2',
            action='feedb',
            target_id='test_repo'
        )

        assert chat_id in AWAITING_FEEDBACK_CACHE
        assert AWAITING_FEEDBACK_CACHE[chat_id]['post'] == 'Contenido original'
        # Verify prompt sent to user
        assert any('feedback' in str(call).lower() for call in mock_tg.call_args_list)

def test_handle_user_text_message_applies_feedback():
    from bot import handle_user_text_message, USER_DRAFTS_CACHE, AWAITING_FEEDBACK_CACHE
    from unittest.mock import MagicMock, patch

    chat_id = 777
    AWAITING_FEEDBACK_CACHE[chat_id] = {
        'repo_name': 'test/my-repo',
        'post': 'Post original sobre Redis',
        'first_comment': 'Comentario',
        'carousel_script': '',
        'language': 'es',
    }

    with patch('bot.refine_post_with_feedback') as mock_refine, patch('bot.send_single_project_draft') as mock_send:
        mock_refine.return_value = {
            'post': 'Post ajustado con 60ms',
            'used_model': 'anthropic/claude-sonnet-4.5',
            'humanizer_qc': {'overall_score': 5.0, 'passed': True},
            'repo_name': 'test/my-repo',
            'language': 'es',
        }
        mock_send.return_value = True

        handle_user_text_message(
            bot_token='fake_token',
            chat_id=chat_id,
            raw_text='Agrega metricas de p99',
        )

        assert chat_id not in AWAITING_FEEDBACK_CACHE
        assert USER_DRAFTS_CACHE[chat_id]['post'] == 'Post ajustado con 60ms'
        mock_refine.assert_called_once()
        mock_send.assert_called_once()

def test_handle_user_text_message_cancellation():
    from bot import handle_user_text_message, AWAITING_FEEDBACK_CACHE
    from unittest.mock import patch

    chat_id = 555
    AWAITING_FEEDBACK_CACHE[chat_id] = {'post': 'Draft'}

    with patch('bot.telegram_api_request') as mock_tg:
        handle_user_text_message(
            bot_token='fake_token',
            chat_id=chat_id,
            raw_text='/cancelar',
        )

        assert chat_id not in AWAITING_FEEDBACK_CACHE
        assert any('cancelados' in str(call).lower() for call in mock_tg.call_args_list)


def test_handle_user_text_message_multi_round_feedback():
    from bot import handle_user_text_message, USER_DRAFTS_CACHE, AWAITING_FEEDBACK_CACHE
    from unittest.mock import patch

    chat_id = 444
    USER_DRAFTS_CACHE[chat_id] = {'post': 'V1'}
    AWAITING_FEEDBACK_CACHE[chat_id] = {'post': 'V1', 'repo_name': 'test/repo'}

    with patch('bot.refine_post_with_feedback') as mock_refine, patch('bot.send_single_project_draft'):
        # Round 1
        mock_refine.return_value = {'post': 'V2', 'used_model': 'LLM', 'repo_name': 'test/repo'}
        handle_user_text_message(bot_token='fake_token', chat_id=chat_id, raw_text='Hazlo mas corto')
        assert USER_DRAFTS_CACHE[chat_id]['post'] == 'V2'

        # User triggers feedback again
        AWAITING_FEEDBACK_CACHE[chat_id] = USER_DRAFTS_CACHE[chat_id]

        # Round 2
        mock_refine.return_value = {'post': 'V3 (Final)', 'used_model': 'LLM', 'repo_name': 'test/repo'}
        handle_user_text_message(bot_token='fake_token', chat_id=chat_id, raw_text='Agrega metricas')
        assert USER_DRAFTS_CACHE[chat_id]['post'] == 'V3 (Final)'


def test_handle_approval_callback_extracts_post_when_cache_empty():
    from bot import handle_approval_callback, USER_DRAFTS_CACHE
    from unittest.mock import MagicMock, patch

    chat_id = 111
    USER_DRAFTS_CACHE.pop(chat_id, None)

    raw_msg = (
        "Proyecto: user/repo\n"
        "POST DE LINKEDIN (Toca para copiar):\n"
        "Post extraido directamente del mensaje de Telegram\n"
        "#Tech"
    )

    with patch('bot.BackendSelector') as mock_bs, patch('bot.telegram_api_request') as mock_tg:
        mock_instance = MagicMock()
        mock_instance.publish.return_value = {'status': 'published', 'raw': {'postGroupId': 'post-xyz'}}
        mock_bs.return_value = mock_instance

        handle_approval_callback(
            bot_token='fake_token',
            chat_id=chat_id,
            callback_id='cb_3',
            action='publi',
            target_id='user_repo',
            message_text=raw_msg,
        )

        mock_instance.publish.assert_called_once()
        published_text = mock_instance.publish.call_args.kwargs.get('text') or mock_instance.publish.call_args[0][0]
        assert 'Post extraido directamente' in published_text


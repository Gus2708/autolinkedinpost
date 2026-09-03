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

        # Verify publish called with draft text
        mock_instance.publish.assert_called_once_with(text='Contenido del post para LinkedIn')
        # Verify telegram notification sent
        assert any('publicado' in str(call).lower() for call in mock_tg.call_args_list)


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

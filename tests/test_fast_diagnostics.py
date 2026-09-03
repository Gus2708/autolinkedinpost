# Tests de diagnostico rapido y cero-costo
import io
import pytest
from unittest.mock import MagicMock, patch
from bot import is_authorized, extract_post_from_telegram_message, HealthCheckHandler
from src.telegram_notifier import send_telegram_project_drafts
from src.linkedin.clients.publora import PubloraClient

def test_cron_drafts_guarantees_approval_buttons():
    with patch('src.telegram_notifier.send_single_project_draft') as mock_send:
        mock_send.return_value = True
        drafts = [
            {'repo_name': 'test/repo-1', 'post': 'Post 1'},
            {'repo_name': 'test/repo-2', 'post': 'Post 2'},
        ]
        ok = send_telegram_project_drafts('dummy_token', '12345', drafts)
        assert ok is True
        assert mock_send.call_count == 2
        for call in mock_send.call_args_list:
            reply_markup = call.kwargs.get('reply_markup')
            assert reply_markup is not None
            assert 'inline_keyboard' in reply_markup
            row = reply_markup['inline_keyboard'][0]
            assert any(b['callback_data'].startswith('publi_') for b in row)
            assert any(b['callback_data'].startswith('feedb_') for b in row)

def test_authorization_matrix():
    assert is_authorized(8520840014, '8520840014') is True
    assert is_authorized('8520840014', '8520840014') is True
    assert is_authorized(9999999999, '8520840014') is False
    assert is_authorized(None, '8520840014') is False
    assert is_authorized(12345, None) is True
    assert is_authorized(12345, '') is True

def test_publora_complete_media_orchestration(monkeypatch):
    client = PubloraClient(api_key='test_key', platform_id='test_plat')
    r_create = MagicMock(ok=True, status_code=200)
    r_create.json.return_value = {'postGroupId': 'grp_999'}
    r_upload = MagicMock(ok=True, status_code=200)
    r_upload.json.return_value = {'uploadUrl': 'https://s3.aws.com/doc', 'mediaId': 'med_888'}
    r_complete = MagicMock(ok=True, status_code=200)
    r_complete.json.return_value = {'success': True, 'mediaFile': {'status': 'ready'}}
    r_update = MagicMock(ok=True, status_code=200)
    r_update.json.return_value = {'success': True}

    client.session.post = MagicMock(side_effect=[r_create, r_upload, r_complete])
    client.session.put = MagicMock(return_value=r_update)
    mock_s3 = MagicMock(return_value=MagicMock(ok=True, status_code=200))
    monkeypatch.setattr('requests.put', mock_s3)

    res = client.create_post(text='Hello LinkedIn', pdf_bytes=b'%PDF-test')
    assert res['postGroupId'] == 'grp_999'
    client.session.post.assert_any_call(
        'https://api.publora.com/api/v1/complete-media/med_888',
        json={'postGroupId': 'grp_999'},
        headers={'x-publora-key': 'test_key', 'Authorization': 'Bearer test_key', 'Content-Type': 'application/json'},
        timeout=15,
    )

def test_extract_post_from_telegram_message_edge_cases():
    raw_telegram = 'Proyecto [1/1]: test\n\nPOST DE LINKEDIN (Toca para copiar):\nTexto del post.\n#Tag'
    extracted = extract_post_from_telegram_message(raw_telegram)
    assert extracted == 'Texto del post.\n#Tag'

    raw_plain = 'Este es un texto largo que un usuario podria enviar directamente.'
    assert extract_post_from_telegram_message(raw_plain) == raw_plain
    assert extract_post_from_telegram_message('') is None
    assert extract_post_from_telegram_message('Hola') is None

def test_healthcheck_handler_response():
    handler = HealthCheckHandler.__new__(HealthCheckHandler)
    handler.wfile = io.BytesIO()
    handler.send_response = MagicMock()
    handler.send_header = MagicMock()
    handler.end_headers = MagicMock()
    handler.do_GET()
    handler.send_response.assert_called_once_with(200)
    assert b'Auto LinkedIn Post Bot is running OK!' in handler.wfile.getvalue()

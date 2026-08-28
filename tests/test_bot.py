"""Tests del bot interactivo: parseo de comandos y control de acceso."""

import pytest

from bot import cache_user_repos, is_authorized, parse_command, MAX_CACHED_CHATS, USER_REPOS_CACHE


class TestParseCommand:
    """El parseo anterior reventaba con IndexError y tiraba abajo el lote de updates."""

    @pytest.mark.parametrize("text", ["@mybot", "@", "@@", "@alguien hola"])
    def test_mentions_do_not_crash(self, text):
        assert parse_command(text) == ""

    @pytest.mark.parametrize("text", ["", "   ", "hola que tal", "menu sin barra"])
    def test_non_commands_return_empty(self, text):
        assert parse_command(text) == ""

    @pytest.mark.parametrize(
        "text,expected",
        [
            ("/menu", "/menu"),
            ("/MENU", "/menu"),
            ("/menu@MiBot", "/menu"),
            ("/menu argumento extra", "/menu"),
            ("  /proyectos  ", "/proyectos"),
        ],
    )
    def test_valid_commands(self, text, expected):
        assert parse_command(text) == expected


class TestAuthorization:
    def test_open_when_no_chat_configured(self):
        assert is_authorized(12345, None) is True

    def test_matching_chat_allowed(self):
        assert is_authorized(12345, "12345") is True

    def test_other_chat_rejected(self):
        assert is_authorized(99999, "12345") is False

    def test_missing_chat_id_rejected_when_restricted(self):
        assert is_authorized(None, "12345") is False


class TestReposCache:
    """El cache crecía sin límite en un proceso de larga vida."""

    def setup_method(self):
        USER_REPOS_CACHE.clear()

    def teardown_method(self):
        USER_REPOS_CACHE.clear()

    def test_stores_and_retrieves(self):
        cache_user_repos(1, [{"name": "repo"}])
        assert USER_REPOS_CACHE[1] == [{"name": "repo"}]

    def test_evicts_oldest_beyond_the_cap(self):
        for chat_id in range(MAX_CACHED_CHATS + 10):
            cache_user_repos(chat_id, [{"name": f"repo{chat_id}"}])
        assert len(USER_REPOS_CACHE) == MAX_CACHED_CHATS
        assert 0 not in USER_REPOS_CACHE
        assert MAX_CACHED_CHATS + 9 in USER_REPOS_CACHE

    def test_refreshing_a_chat_keeps_it_alive(self):
        cache_user_repos(0, [{"name": "primero"}])
        for chat_id in range(1, MAX_CACHED_CHATS):
            cache_user_repos(chat_id, [{"name": f"repo{chat_id}"}])
        cache_user_repos(0, [{"name": "refrescado"}])  # vuelve al final de la cola
        cache_user_repos(999, [{"name": "nuevo"}])
        assert 0 in USER_REPOS_CACHE

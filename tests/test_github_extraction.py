"""Tests de la extracción de actividad de GitHub: relevancia y autoría de commits."""

import pytest

from src.github_extractor import fetch_recent_github_activity, is_meaningful_commit, is_own_commit


class FakeResponse:
    """Respuesta mínima compatible con lo que consume el extractor."""

    def __init__(self, payload, status_code=200, headers=None, text=""):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text

    def json(self):
        return self._payload


class TestIsMeaningfulCommit:
    @pytest.mark.parametrize(
        "message",
        [
            "merge branch 'main' into develop",
            "Merge pull request #42 from user/branch",
            "fix typo",
            "bump version",
            "chore(deps): update lockfile",
            "wip",
            "update readme",
            "initial commit",
            "abc",
        ],
    )
    def test_trivial_commits_are_rejected(self, message):
        assert is_meaningful_commit(message) is False

    @pytest.mark.parametrize(
        "message",
        [
            "feat(auth): migrate token rotation to redis with exponential backoff",
            "perf(db): remove n+1 queries in billing aggregation",
            "fix(rate-limit): prevent race condition in sliding window limiter",
            "refactor(cqrs): implement outbox pattern for event consistency",
        ],
    )
    def test_substantive_commits_are_kept(self, message):
        assert is_meaningful_commit(message) is True

    def test_case_insensitive(self):
        assert is_meaningful_commit("MERGE BRANCH main") is False


class TestIsOwnCommit:
    """El parámetro `author` de la API sólo ve commits que GitHub logró vincular
    mediante un email verificado, así que el filtrado se hace del lado del cliente."""

    def test_linked_login_matches(self):
        commit = {"author": {"login": "GusDev"}, "commit": {"author": {}}}
        assert is_own_commit(commit, "gusdev") is True

    def test_linked_login_of_someone_else(self):
        commit = {"author": {"login": "otra-persona"}, "commit": {"author": {"name": "gusdev"}}}
        assert is_own_commit(commit, "gusdev") is False

    def test_unlinked_github_noreply_email(self):
        commit = {"author": None, "commit": {"author": {"email": "123+gusdev@users.noreply.github.com"}}}
        assert is_own_commit(commit, "gusdev") is True

    def test_unlinked_noreply_of_someone_else(self):
        commit = {"author": None, "commit": {"author": {"email": "99+otro@users.noreply.github.com"}}}
        assert is_own_commit(commit, "gusdev") is False

    def test_unlinked_configured_email(self):
        commit = {"author": None, "commit": {"author": {"email": "MI@correo.com"}}}
        assert is_own_commit(commit, "gusdev", ["mi@correo.com"]) is True

    def test_unlinked_author_name(self):
        commit = {"author": None, "commit": {"author": {"name": "GusDev", "email": "raro@x.com"}}}
        assert is_own_commit(commit, "gusdev") is True

    def test_unrelated_commit_rejected(self):
        commit = {"author": None, "commit": {"author": {"name": "Ajeno", "email": "a@b.com"}}}
        assert is_own_commit(commit, "gusdev") is False

    def test_ci_bot_rejected(self):
        commit = {"author": {"login": "github-actions[bot]"}, "commit": {"author": {}}}
        assert is_own_commit(commit, "gusdev") is False


class TestFetchRecentActivity:
    """El extractor pedía todos los commits del repo sin mirar quién los escribió."""

    @staticmethod
    def _patch_api(monkeypatch, commits):
        def fake_get(url, **kwargs):
            if "/repos?" in url or url.endswith("/repos"):
                return FakeResponse([{"full_name": "user/proyecto", "pushed_at": "2999-01-01T00:00:00Z"}])
            if "/commits" in url:
                return FakeResponse(commits)
            return FakeResponse([])

        monkeypatch.setattr("src.github_extractor.requests.get", fake_get)

    def test_foreign_commits_are_filtered_out(self, monkeypatch):
        self._patch_api(monkeypatch, [
            {
                "author": {"login": "user"},
                "commit": {"author": {"date": "2999-01-01T00:00:00Z"}, "message": "feat(api): add retry with backoff"},
            },
            {
                "author": {"login": "colega"},
                "commit": {"author": {"date": "2999-01-01T00:00:00Z"}, "message": "feat(ui): redesign the settings panel"},
            },
        ])
        commits = fetch_recent_github_activity("user", token=None, lookback_days=1).get("user/proyecto", [])
        assert any("retry with backoff" in c for c in commits)
        assert not any("settings panel" in c for c in commits)

    def test_unlinked_own_commit_is_kept(self, monkeypatch):
        """Regresión: `author=login` descartaba los commits propios sin vincular."""
        self._patch_api(monkeypatch, [{
            "author": None,
            "commit": {
                "author": {"name": "user", "email": "sin-verificar@ejemplo.com", "date": "2999-01-01T00:00:00Z"},
                "message": "perf(db): drop the n+1 in billing aggregation",
            },
        }])
        commits = fetch_recent_github_activity("user", token=None, lookback_days=1).get("user/proyecto", [])
        assert any("n+1" in c for c in commits)

    def test_commits_query_no_longer_uses_author_param(self, monkeypatch):
        called_urls = []

        def fake_get(url, **kwargs):
            called_urls.append(url)
            if "/repos?" in url or url.endswith("/repos"):
                return FakeResponse([{"full_name": "user/proyecto", "pushed_at": "2999-01-01T00:00:00Z"}])
            return FakeResponse([])

        monkeypatch.setattr("src.github_extractor.requests.get", fake_get)
        fetch_recent_github_activity("user", token=None, lookback_days=1)

        commit_calls = [u for u in called_urls if "/commits" in u]
        assert commit_calls, "no se consultaron commits"
        assert all("author=" not in u for u in commit_calls)

    def test_since_iso_string_filters_older_commits(self, monkeypatch):
        self._patch_api(monkeypatch, [
            {
                "author": {"login": "user"},
                "commit": {"author": {"date": "2026-08-30T22:00:00Z"}, "message": "feat(core): nuevo commit despues de la corrida"},
            },
            {
                "author": {"login": "user"},
                "commit": {"author": {"date": "2026-08-30T20:00:00Z"}, "message": "feat(old): commit viejo antes de la corrida"},
            },
        ])
        commits = fetch_recent_github_activity(
            "user",
            token=None,
            since="2026-08-30T21:00:00Z",
        ).get("user/proyecto", [])
        assert any("nuevo commit" in c for c in commits)
        assert not any("commit viejo" in c for c in commits)

    def test_since_datetime_object(self, monkeypatch):
        from datetime import datetime, timezone
        self._patch_api(monkeypatch, [
            {
                "author": {"login": "user"},
                "commit": {"author": {"date": "2026-08-30T22:00:00Z"}, "message": "feat(core): nuevo commit con datetime"},
            },
            {
                "author": {"login": "user"},
                "commit": {"author": {"date": "2026-08-30T20:00:00Z"}, "message": "feat(old): commit anterior"},
            },
        ])
        cutoff = datetime(2026, 8, 30, 21, 0, 0, tzinfo=timezone.utc)
        commits = fetch_recent_github_activity(
            "user",
            token=None,
            since=cutoff,
        ).get("user/proyecto", [])
        assert any("nuevo commit con datetime" in c for c in commits)
        assert not any("commit anterior" in c for c in commits)

    def test_user_repos_fallback_to_public_url(self, monkeypatch):
        """Si /user/repos responde 403 (ej: token de CI sin scope de usuario), cae a /users/{user}/repos."""
        called_urls = []

        def fake_get(url, **kwargs):
            called_urls.append(url)
            if "/user/repos" in url:
                # 403 Resource not accessible by integration (not rate limit)
                return FakeResponse([], status_code=403, headers={"X-RateLimit-Remaining": "5000"}, text="Resource not accessible")
            if "/users/sample-user/repos" in url:
                return FakeResponse([{"full_name": "example-org/sample-repo", "pushed_at": "2999-01-01T00:00:00Z"}])
            if "/commits" in url:
                return FakeResponse([
                    {
                        "author": {"login": "sample-user"},
                        "commit": {"author": {"date": "2999-01-01T00:00:00Z"}, "message": "feat(api): fallback works"},
                    }
                ])
            return FakeResponse([])

        monkeypatch.setattr("src.github_extractor.requests.get", fake_get)
        activity = fetch_recent_github_activity("sample-user", token="ci_token", lookback_days=1)
        assert any("/user/repos" in u for u in called_urls)
        assert any("/users/sample-user/repos" in u for u in called_urls)
        assert "example-org/sample-repo" in activity

    def test_rate_limit_raises_runtime_error_when_no_commits(self, monkeypatch):
        """Si la API aplica rate limit y no hay commits, no silencia el fallo con {} sino que lanza RuntimeError."""
        def fake_get(url, **kwargs):
            return FakeResponse(
                {"message": "API rate limit exceeded"},
                status_code=403,
                headers={"X-RateLimit-Remaining": "0", "X-RateLimit-Reset": "1900000000"},
                text="API rate limit exceeded",
            )

        monkeypatch.setattr("src.github_extractor.requests.get", fake_get)
        with pytest.raises(RuntimeError) as exc_info:
            fetch_recent_github_activity("sample-user", token=None, lookback_days=1)
        assert "rate limit" in str(exc_info.value).lower()



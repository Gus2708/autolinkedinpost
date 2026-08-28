"""Módulo de extracción y filtrado de actividad reciente de GitHub."""

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
import requests


TRIVIAL_EXACT_OR_PREFIX = [
    "merge branch",
    "merge pull request",
    "fix typo",
    "bump version",
    "bump deps",
    "chore(deps)",
    "format code",
    "lint fix",
    "initial commit",
]


def _warn_on_rate_limit(response: requests.Response, context: str) -> bool:
    """Avisa cuando GitHub cortó por rate limit en vez de fallar en silencio.

    Sin token el límite es de 60 requests/hora, y esta función hace varias por repo:
    el modo anterior (tragar cualquier status != 200) hacía que el bot informara
    'no hay actividad hoy' cuando en realidad lo habían frenado.
    """
    if response.status_code not in (403, 429):
        return False

    remaining = response.headers.get("X-RateLimit-Remaining")
    if remaining == "0" or response.status_code == 429:
        reset = response.headers.get("X-RateLimit-Reset", "")
        reset_txt = ""
        if reset.isdigit():
            reset_at = datetime.fromtimestamp(int(reset), tz=timezone.utc)
            reset_txt = f" Se restablece a las {reset_at:%H:%M} UTC."
        print(
            f"[ERROR] GitHub aplicó rate limit durante {context}.{reset_txt} "
            "Configurá GH_TOKEN para subir el límite de 60 a 5000 requests/hora."
        )
        return True

    print(f"[WARN] GitHub respondió 403 en {context}: {response.text[:120]}")
    return True


def get_author_emails() -> List[str]:
    """Emails adicionales del autor, para reconocer commits que GitHub no vinculó.

    Se leen de GH_AUTHOR_EMAILS (separados por coma). Sirve cuando se commitea desde
    una máquina cuyo git config apunta a un correo no verificado en la cuenta.
    """
    raw = os.getenv("GH_AUTHOR_EMAILS", "")
    return [e.strip().lower() for e in raw.split(",") if e.strip()]


def is_own_commit(
    commit_obj: Dict[str, Any],
    username: str,
    author_emails: Optional[List[str]] = None,
) -> bool:
    """Determina si un commit es del usuario, tolerando commits sin vincular.

    Se aplican tres criterios en orden de confiabilidad:
    1. El login que GitHub asoció al commit (el más fiable cuando existe).
    2. El email del autor, contra GH_AUTHOR_EMAILS y contra el patrón noreply de GitHub.
    3. El nombre del autor en el commit, como último recurso.
    """
    user_lower = username.lower()

    # 1. Login vinculado por GitHub.
    linked = commit_obj.get("author")
    if isinstance(linked, dict) and linked.get("login"):
        return linked["login"].lower() == user_lower

    # Sin vínculo, comparar los datos crudos del commit.
    commit_author = (commit_obj.get("commit", {}) or {}).get("author", {}) or {}
    email = (commit_author.get("email") or "").lower()
    name = (commit_author.get("name") or "").lower()

    # 2. Email declarado o el noreply que GitHub genera (12345+usuario@users.noreply.github.com).
    if email:
        if email in (author_emails or []):
            return True
        if email.endswith("@users.noreply.github.com"):
            local = email.split("@")[0]
            handle = local.split("+")[-1]
            if handle == user_lower:
                return True

    # 3. Nombre del autor.
    return name == user_lower


def is_meaningful_commit(message: str) -> bool:
    """Determina si un mensaje de commit aporta valor técnico para un post."""
    msg_lower = message.strip().lower()
    if len(msg_lower) < 6:
        return False

    # Descartar commits puramente triviales como "update readme" o "fix typo"
    if msg_lower in ["update readme", "update readme.md", "wip", "cleanup", "fix typo", "fixes"]:
        return False

    # Si contiene prefijos de merges o chores sin descripción sustancial
    for keyword in TRIVIAL_EXACT_OR_PREFIX:
        if msg_lower.startswith(keyword) or keyword == msg_lower:
            return False

    return True


def fetch_recent_github_activity(
    username: str,
    token: Optional[str] = None,
    lookback_days: int = 7,
) -> Dict[str, List[str]]:
    """Obtiene commits y actividad de los últimos N días combinando Events API y Commits directos por repositorio."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AutoLinkedInPost/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    cutoff_iso = cutoff_date.isoformat()
    repo_commits: Dict[str, List[str]] = {}

    author_emails = get_author_emails()

    def add_commit(repo: str, message: str) -> None:
        """Agrega un mensaje al repo evitando duplicados."""
        bucket = repo_commits.setdefault(repo, [])
        if message not in bucket:
            bucket.append(message)

    # 1. Consultar repositorios recientemente modificados del usuario.
    # Con token usamos /user/repos, que incluye repos privados y de organizaciones;
    # sin token sólo se ven los públicos del perfil.
    try:
        if token:
            repos_url = "https://api.github.com/user/repos?sort=pushed&per_page=30&affiliation=owner,collaborator,organization_member"
        else:
            repos_url = f"https://api.github.com/users/{username}/repos?sort=pushed&per_page=30"

        repos_res = requests.get(repos_url, headers=headers, timeout=15)
        _warn_on_rate_limit(repos_res, "listado de repositorios")

        if repos_res.status_code == 200:
            user_repos = repos_res.json()
            if not isinstance(user_repos, list):
                user_repos = []
            for repo_data in user_repos:
                pushed_at_str = repo_data.get("pushed_at")
                if not pushed_at_str:
                    continue
                pushed_at = datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))
                if pushed_at < cutoff_date:
                    continue

                repo_full_name = repo_data.get("full_name")
                if not repo_full_name:
                    continue

                # Se pide sin el parámetro `author` de la API y se filtra del lado del
                # cliente: `author=login` sólo matchea los commits que GitHub logró
                # vincular a la cuenta mediante un email verificado, así que un commit
                # hecho con otro email quedaba fuera y el repo aparecía sin actividad.
                commits_url = (
                    f"https://api.github.com/repos/{repo_full_name}/commits"
                    f"?since={cutoff_iso}&per_page=30"
                )
                c_res = requests.get(commits_url, headers=headers, timeout=15)
                _warn_on_rate_limit(c_res, f"commits de {repo_full_name}")

                if c_res.status_code != 200:
                    continue

                commit_list = c_res.json()
                if not isinstance(commit_list, list):
                    continue

                skipped_others = 0
                for commit_obj in commit_list:
                    commit_meta = commit_obj.get("commit", {})
                    committer_date_str = (
                        commit_meta.get("committer", {}).get("date")
                        or commit_meta.get("author", {}).get("date")
                    )
                    if committer_date_str:
                        c_date = datetime.fromisoformat(committer_date_str.replace("Z", "+00:00"))
                        if c_date < cutoff_date:
                            continue

                    if not is_own_commit(commit_obj, username, author_emails):
                        skipped_others += 1
                        continue

                    raw_msg = commit_meta.get("message", "")
                    first_line = raw_msg.split("\n")[0].strip()
                    if is_meaningful_commit(first_line):
                        add_commit(repo_full_name, first_line)

                if skipped_others:
                    print(f"[INFO] {repo_full_name}: {skipped_others} commit(s) de otros autores descartados.")
    except requests.RequestException as e:
        print(f"[WARN] Error de red consultando repositorios directos: {e}")
    except (ValueError, KeyError) as e:
        print(f"[WARN] Respuesta inesperada de la API de repositorios: {e}")

    # 2. Consultar Events API para capturar PRs, Tags y releases
    events_url = f"https://api.github.com/users/{username}/events?per_page=100"
    try:
        response = requests.get(events_url, headers=headers, timeout=15)
        _warn_on_rate_limit(response, "Events API")

        if response.status_code == 200:
            events = response.json()
            if not isinstance(events, list):
                events = []
            for event in events:
                event_type = event.get("type")
                created_at_str = event.get("created_at")
                if not created_at_str:
                    continue

                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                if created_at < cutoff_date:
                    continue

                # La Events API de un usuario ya viene acotada a su actividad, pero el
                # actor se verifica igual para no arrastrar eventos de terceros.
                actor = (event.get("actor") or {}).get("login", "")
                if actor and actor.lower() != username.lower():
                    continue

                repo_name = event.get("repo", {}).get("name", "unknown-repo")
                payload = event.get("payload", {})

                if event_type == "PushEvent":
                    for commit in payload.get("commits", []):
                        msg = commit.get("message", "").split("\n")[0].strip()
                        if is_meaningful_commit(msg):
                            add_commit(repo_name, msg)

                elif event_type == "PullRequestEvent":
                    action = payload.get("action")
                    pr = payload.get("pull_request", {})
                    # Sólo interesan los PRs que el usuario abrió o que se mergearon.
                    # La condición anterior mezclaba `and`/`or` sin paréntesis y el
                    # último término hacía redundante a todo el resto.
                    is_relevant = action == "opened" or (action == "closed" and pr.get("merged", False))
                    if is_relevant:
                        title = pr.get("title", "").strip()
                        body = (pr.get("body") or "").split("\n")[0].strip()
                        summary = f"PR: {title}" + (f" ({body})" if body and len(body) < 100 else "")
                        if is_meaningful_commit(summary):
                            add_commit(repo_name, summary)

                elif event_type == "CreateEvent":
                    ref_type = payload.get("ref_type")
                    ref = payload.get("ref")
                    description = payload.get("description") or ""
                    if ref_type == "repository":
                        summary = f"Created repository {repo_name}" + (f": {description}" if description else "")
                        add_commit(repo_name, summary)
                    elif ref_type == "tag" and ref:
                        add_commit(repo_name, f"Tagged release/version: {ref}")
    except requests.RequestException as e:
        print(f"[WARN] Error de red consultando GitHub Events API: {e}")
    except (ValueError, KeyError) as e:
        print(f"[WARN] Respuesta inesperada de GitHub Events API: {e}")

    return repo_commits



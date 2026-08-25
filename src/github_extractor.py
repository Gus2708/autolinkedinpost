"""Módulo de extracción y filtrado de actividad reciente de GitHub."""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional
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

    # 1. Consultar repositorios recientemente modificados del usuario
    try:
        repos_url = f"https://api.github.com/users/{username}/repos?sort=pushed&per_page=12"
        repos_res = requests.get(repos_url, headers=headers, timeout=12)
        if repos_res.status_code == 200:
            user_repos = repos_res.json()
            for repo_data in user_repos:
                pushed_at_str = repo_data.get("pushed_at")
                if not pushed_at_str:
                    continue
                pushed_at = datetime.fromisoformat(pushed_at_str.replace("Z", "+00:00"))
                if pushed_at < cutoff_date:
                    continue

                repo_full_name = repo_data.get("full_name")
                commits_url = f"https://api.github.com/repos/{repo_full_name}/commits?since={cutoff_iso}&per_page=20"
                c_res = requests.get(commits_url, headers=headers, timeout=10)
                if c_res.status_code == 200:
                    for commit_obj in c_res.json():
                        commit_meta = commit_obj.get("commit", {})
                        committer_date_str = commit_meta.get("committer", {}).get("date") or commit_meta.get("author", {}).get("date")
                        if committer_date_str:
                            c_date = datetime.fromisoformat(committer_date_str.replace("Z", "+00:00"))
                            if c_date < cutoff_date:
                                continue

                        raw_msg = commit_meta.get("message", "")
                        first_line = raw_msg.split("\n")[0].strip()
                        if is_meaningful_commit(first_line):
                            repo_commits.setdefault(repo_full_name, [])
                            if first_line not in repo_commits[repo_full_name]:
                                repo_commits[repo_full_name].append(first_line)
    except Exception as e:
        print(f"[WARN] Error consultando repositorios directos: {e}")

    # 2. Consultar Events API para capturar PRs, Tags y releases
    events_url = f"https://api.github.com/users/{username}/events"
    try:
        response = requests.get(events_url, headers=headers, timeout=15)
        if response.status_code == 200:
            events = response.json()
            for event in events:
                event_type = event.get("type")
                created_at_str = event.get("created_at")
                if not created_at_str:
                    continue

                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                if created_at < cutoff_date:
                    continue

                repo_name = event.get("repo", {}).get("name", "unknown-repo")

                if event_type == "PushEvent":
                    payload = event.get("payload", {})
                    commits = payload.get("commits", [])
                    if commits:
                        for commit in commits:
                            msg = commit.get("message", "").split("\n")[0].strip()
                            if is_meaningful_commit(msg):
                                repo_commits.setdefault(repo_name, [])
                                if msg not in repo_commits[repo_name]:
                                    repo_commits[repo_name].append(msg)

                elif event_type == "PullRequestEvent":
                    action = event.get("payload", {}).get("action")
                    pr = event.get("payload", {}).get("pull_request", {})
                    if action in ["opened", "closed"] and pr.get("merged", False) or action == "opened":
                        title = pr.get("title", "").strip()
                        body = (pr.get("body") or "").split("\n")[0].strip()
                        summary = f"PR: {title}" + (f" ({body})" if body and len(body) < 100 else "")
                        if is_meaningful_commit(summary):
                            repo_commits.setdefault(repo_name, [])
                            if summary not in repo_commits[repo_name]:
                                repo_commits[repo_name].append(summary)

                elif event_type == "CreateEvent":
                    ref_type = event.get("payload", {}).get("ref_type")
                    ref = event.get("payload", {}).get("ref")
                    description = event.get("payload", {}).get("description") or ""
                    if ref_type == "repository":
                        summary = f"Created repository {repo_name}" + (f": {description}" if description else "")
                        repo_commits.setdefault(repo_name, [])
                        if summary not in repo_commits[repo_name]:
                            repo_commits[repo_name].append(summary)
                    elif ref_type == "tag" and ref:
                        summary = f"Tagged release/version: {ref}"
                        repo_commits.setdefault(repo_name, [])
                        if summary not in repo_commits[repo_name]:
                            repo_commits[repo_name].append(summary)
    except Exception as e:
        print(f"[WARN] Error al consultar GitHub Events API: {e}")

    return repo_commits


def format_commits_for_llm(repo_activity: Dict[str, List[str]]) -> str:
    """Formatea la actividad agrupada por repo en texto estructurado para el prompt."""
    if not repo_activity:
        return ""

    lines = []
    for repo, commits in repo_activity.items():
        lines.append(f"### Repositorio: {repo}")
        for commit in commits:
            lines.append(f"- {commit}")
        lines.append("")

    return "\n".join(lines)

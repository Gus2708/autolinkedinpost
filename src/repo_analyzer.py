"""Módulo de análisis profundo de repositorios para posts de showcase/portafolio."""

import base64
from typing import Any, Dict, List, Optional
import requests


def fetch_user_repositories(
    username: str,
    token: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Obtiene la lista de repositorios del usuario ordenados por última actualización."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AutoLinkedInPost/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
        url = "https://api.github.com/user/repos?sort=pushed&per_page=100&affiliation=owner"
    else:
        url = f"https://api.github.com/users/{username}/repos?sort=pushed&per_page=100"

    try:
        res = requests.get(url, headers=headers, timeout=15)
        if res.status_code != 200:
            # Fallback a endpoint público si falla /user/repos
            url = f"https://api.github.com/users/{username}/repos?sort=pushed&per_page=100"
            res = requests.get(url, headers=headers, timeout=15)
            res.raise_for_status()

        repos = res.json()
        if not isinstance(repos, list):
            return []

        # Filtrar forks a menos que tengan descripción
        clean_repos = []
        for r in repos:
            if not r.get("fork") or r.get("description"):
                clean_repos.append({
                    "name": r.get("name"),
                    "full_name": r.get("full_name"),
                    "description": r.get("description") or "Sin descripción",
                    "language": r.get("language") or "General",
                    "stars": r.get("stargazers_count", 0),
                    "updated_at": r.get("pushed_at") or r.get("updated_at"),
                })
        return clean_repos
    except requests.RequestException as e:
        print(f"[ERROR] Error al listar repositorios para @{username}: {e}")
        return []


def fetch_repository_deep_context(
    repo_full_name: str,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    """Descarga README, lenguajes y estructura de archivos para un análisis arquitectónico completo."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AutoLinkedInPost/1.0",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    base_url = f"https://api.github.com/repos/{repo_full_name}"

    context = {
        "full_name": repo_full_name,
        "name": repo_full_name.split("/")[-1],
        "description": "",
        "languages": [],
        "readme": "",
        "key_files": [],
        "stars": 0,
        "html_url": f"https://github.com/{repo_full_name}",
    }

    # 1. Metadata básica
    try:
        res = requests.get(base_url, headers=headers, timeout=10)
        if res.status_code == 200:
            data = res.json()
            context["description"] = data.get("description") or ""
            context["stars"] = data.get("stargazers_count", 0)
    except Exception:
        pass

    # 2. Lenguajes utilizados
    try:
        lang_res = requests.get(f"{base_url}/languages", headers=headers, timeout=10)
        if lang_res.status_code == 200:
            context["languages"] = list(lang_res.json().keys())
    except Exception:
        pass

    # 3. Contenido del README
    try:
        readme_res = requests.get(f"{base_url}/readme", headers=headers, timeout=10)
        if readme_res.status_code == 200:
            readme_json = readme_res.json()
            content_b64 = readme_json.get("content", "")
            if content_b64:
                decoded = base64.b64decode(content_b64).decode("utf-8", errors="ignore")
                # Limitar a los primeros 3000 caracteres para el contexto del LLM
                context["readme"] = decoded[:3000]
    except Exception:
        pass

    # 4. Estructura de archivos de la raíz
    try:
        contents_res = requests.get(f"{base_url}/contents", headers=headers, timeout=10)
        if contents_res.status_code == 200:
            files = contents_res.json()
            if isinstance(files, list):
                context["key_files"] = [f.get("name") for f in files if f.get("name")]
    except Exception:
        pass

    return context

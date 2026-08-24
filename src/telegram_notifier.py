"""Módulo de envío de notificaciones y borradores segmentados a Telegram."""

import html
from typing import Dict, List
import requests


def send_single_project_draft(
    bot_token: str,
    chat_id: str,
    repo_name: str,
    post_text: str,
    visual_suggestion: str,
    project_index: int = 1,
    total_projects: int = 1,
) -> bool:
    """Envía el borrador de un proyecto específico a Telegram."""
    if not post_text or post_text.strip().startswith("Error generando post"):
        print(f"[WARN] Omitiendo envío a Telegram para {repo_name} por contenido inválido/error.")
        return False

    safe_repo = html.escape(repo_name)
    safe_post = html.escape(post_text)
    safe_visual = html.escape(visual_suggestion)

    header = (
        f"📦 <b>Proyecto [{project_index}/{total_projects}]: <code>{safe_repo}</code></b>\n\n"
        "📝 <b>Texto del Post para LinkedIn:</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{safe_post}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "📸 <b>Sugerencia de Imagen / Captura:</b>\n"
        f"{safe_visual}\n"
    )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    max_len = 4000
    if len(header) <= max_len:
        payload = {
            "chat_id": chat_id,
            "text": header,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            res = requests.post(url, json=payload, timeout=15)
            res.raise_for_status()
            return True
        except requests.RequestException as e:
            print(f"[ERROR] Falló el envío a Telegram para {repo_name}: {e}")
            return False
    else:
        # Partición si excede límite
        part1 = (
            f"📦 <b>Proyecto [{project_index}/{total_projects}]: <code>{safe_repo}</code></b> (Parte 1: Post)\n\n"
            f"{safe_post}"
        )
        part2 = (
            f"📸 <b>Sugerencia de Imagen para <code>{safe_repo}</code> (Parte 2):</b>\n\n"
            f"{safe_visual}"
        )
        for msg in [part1, part2]:
            payload = {
                "chat_id": chat_id,
                "text": msg,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }
            try:
                res = requests.post(url, json=payload, timeout=15)
                res.raise_for_status()
            except requests.RequestException as e:
                print(f"[ERROR] Falló el envío de fragmento a Telegram: {e}")
                return False
        return True


def send_telegram_project_drafts(
    bot_token: str,
    chat_id: str,
    drafts: List[Dict[str, str]],
) -> bool:
    """Envía todos los borradores segmentados por proyecto a Telegram."""
    if not bot_token or not chat_id:
        print("[ERROR] TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados.")
        return False

    if not drafts:
        print("[INFO] No hay borradores de proyectos para enviar.")
        return True

    total = len(drafts)
    
    # Enviar mensaje resumen introductorio si hay múltiples proyectos
    if total > 1:
        intro = f"🚀 <b>Revisión Diaria: {total} proyectos tuvieron actividad relevante hoy.</b>\nTe envío los borradores individuales a continuación:"
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        try:
            requests.post(url, json={"chat_id": chat_id, "text": intro, "parse_mode": "HTML"}, timeout=10)
        except Exception:
            pass

    all_success = True
    for i, draft in enumerate(drafts, start=1):
        success = send_single_project_draft(
            bot_token=bot_token,
            chat_id=chat_id,
            repo_name=draft["repo_name"],
            post_text=draft["post"],
            visual_suggestion=draft["visual_suggestion"],
            project_index=i,
            total_projects=total,
        )
        if not success:
            all_success = False

    return all_success

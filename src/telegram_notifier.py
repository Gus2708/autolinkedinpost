"""Módulo de envío de notificaciones con bloques 'Tap to Copy' nativos de Telegram."""

import html
from typing import Any, Dict, List
import requests


def send_single_project_draft(
    bot_token: str,
    chat_id: str,
    repo_name: str,
    post_text: str,
    visual_suggestion: str,
    first_comment: str = "",
    carousel_script: str = "",
    quality_score: float = 5.0,
    project_index: int = 1,
    total_projects: int = 1,
) -> bool:
    """Envía el paquete de publicación con bloques <pre> para copiar con un solo toque en Telegram."""
    if not post_text or post_text.strip().startswith("Error generando post"):
        print(f"[WARN] Omitiendo envío a Telegram para {repo_name} por contenido inválido.")
        return False

    safe_repo = html.escape(repo_name)
    safe_post = html.escape(post_text)
    safe_first_comment = html.escape(first_comment)
    safe_visual = html.escape(visual_suggestion)
    safe_carousel = html.escape(carousel_script)

    score_display = f"⭐ <b>Quality Score (LLM Judge):</b> {quality_score:.1f}/5.0\n" if quality_score else ""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    # 1. Mensaje del Post Principal (Con bloque <pre> para copiar en un toque)
    post_message = (
        f"📦 <b>Proyecto [{project_index}/{total_projects}]: <code>{safe_repo}</code></b>\n"
        f"{score_display}\n"
        "📝 <b>POST DE LINKEDIN</b> <i>(Toca el bloque gris para copiarlo todo)</i>:\n"
        f"<pre>{safe_post}</pre>"
    )

    try:
        res = requests.post(url, json={
            "chat_id": chat_id,
            "text": post_message[:4000],
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=15)
        res.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERROR] Falló el envío del post a Telegram para {repo_name}: {e}")
        return False

    # 2. Mensaje de Primer Comentario y Sugerencia Visual
    comment_visual_message = (
        f"💬 <b>PRIMER COMENTARIO (Regla 60 min)</b> <i>(Toca para copiar)</i>:\n"
        f"<pre>{safe_first_comment}</pre>\n\n"
        f"📸 <b>SUGERENCIA VISUAL:</b>\n"
        f"{safe_visual}"
    )

    try:
        requests.post(url, json={
            "chat_id": chat_id,
            "text": comment_visual_message[:4000],
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }, timeout=15)
    except Exception as e:
        print(f"[WARN] Error al enviar primer comentario a Telegram: {e}")

    # 3. Mensaje de Guion de Carrusel PDF (Opcional)
    if safe_carousel and len(safe_carousel.strip()) > 30:
        carousel_message = (
            f"📑 <b>GUION DE CARRUSEL PDF (24% Engagement)</b> <i>(Toca para copiar a Canva)</i>:\n"
            f"<pre>{safe_carousel}</pre>"
        )
        try:
            requests.post(url, json={
                "chat_id": chat_id,
                "text": carousel_message[:4000],
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }, timeout=15)
        except Exception as e:
            print(f"[WARN] Error al enviar guion de carrusel a Telegram: {e}")

    return True


def send_telegram_project_drafts(
    bot_token: str,
    chat_id: str,
    drafts: List[Dict[str, Any]],
) -> bool:
    """Envía todos los paquetes de publicación a Telegram."""
    if not bot_token or not chat_id:
        print("[ERROR] TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados.")
        return False

    if not drafts:
        print("[INFO] No hay borradores para enviar.")
        return True

    total = len(drafts)
    if total > 1:
        intro = f"🚀 <b>Revisión Diaria 2026: {total} proyecto(s) activo(s) hoy.</b>\nTe envío los paquetes optimizados listos para copiar con 1 toque a continuación:"
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
            repo_name=draft.get("repo_name", "proyecto"),
            post_text=draft.get("post", ""),
            visual_suggestion=draft.get("visual_suggestion", ""),
            first_comment=draft.get("first_comment", ""),
            carousel_script=draft.get("carousel_script", ""),
            quality_score=draft.get("quality_score", 5.0),
            project_index=i,
            total_projects=total,
        )
        if not success:
            all_success = False

    return all_success

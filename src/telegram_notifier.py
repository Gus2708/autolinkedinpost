"""Módulo de envío de notificaciones y paquetes completos de publicación a Telegram."""

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
    """Envía el paquete completo de publicación de un proyecto específico a Telegram."""
    if not post_text or post_text.strip().startswith("Error generando post"):
        print(f"[WARN] Omitiendo envío a Telegram para {repo_name} por contenido inválido.")
        return False

    safe_repo = html.escape(repo_name)
    safe_post = html.escape(post_text)
    safe_first_comment = html.escape(first_comment)
    safe_visual = html.escape(visual_suggestion)
    safe_carousel = html.escape(carousel_script)

    score_display = f"⭐ <b>Quality Score (LLM Judge):</b> {quality_score:.1f}/5.0\n\n" if quality_score else ""

    # 1. Mensaje Principal: El Post para LinkedIn
    main_message = (
        f"📦 <b>Proyecto [{project_index}/{total_projects}]: <code>{safe_repo}</code></b>\n"
        f"{score_display}"
        "📝 <b>POST DE LINKEDIN (Mobile-First 2026):</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"{safe_post}\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "💬 <b>PRIMER COMENTARIO (Regla 60 min - Link limpio):</b>\n"
        f"<code>{safe_first_comment}</code>\n\n"
        "📸 <b>SUGERENCIA VISUAL:</b>\n"
        f"{safe_visual}"
    )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    max_len = 4000
    if len(main_message) <= max_len:
        payload = {
            "chat_id": chat_id,
            "text": main_message,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }
        try:
            res = requests.post(url, json=payload, timeout=15)
            res.raise_for_status()
        except requests.RequestException as e:
            print(f"[ERROR] Falló el envío del post principal a Telegram para {repo_name}: {e}")
            return False
    else:
        # Partición si excede límite de 4000 caracteres
        part1 = (
            f"📦 <b>Proyecto [{project_index}/{total_projects}]: <code>{safe_repo}</code></b> (Post)\n"
            f"{score_display}\n"
            f"{safe_post}"
        )
        part2 = (
            f"💬 <b>Primer Comentario & Visual para <code>{safe_repo}</code>:</b>\n\n"
            f"<b>Primer Comentario:</b>\n<code>{safe_first_comment}</code>\n\n"
            f"<b>Sugerencia Visual:</b>\n{safe_visual}"
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

    # 2. Si hay guion de carrusel PDF, enviarlo como mensaje complementario opcional
    if safe_carousel and len(safe_carousel.strip()) > 30:
        carousel_message = (
            f"📑 <b>Guion de Carrusel PDF (24% Engagement) para <code>{safe_repo}</code>:</b>\n\n"
            f"<i>Podés pegar este guion en Canva o Figma (proporción 4:5 vertical) para subirlo como PDF:</i>\n\n"
            f"{safe_carousel}"
        )
        try:
            requests.post(url, json={
                "chat_id": chat_id,
                "text": carousel_message[:4000],
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }, timeout=15)
        except Exception:
            pass

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
        intro = f"🚀 <b>Revisión Diaria 2026: {total} proyecto(s) activo(s) hoy.</b>\nTe envío los paquetes optimizados para LinkedIn a continuación:"
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

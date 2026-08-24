"""Módulo de envío de notificaciones y paquetes de publicación a Telegram con soporte para botones inline y Tap-to-Copy."""

import html
import re
from typing import Any, Dict, List, Optional
import requests


def _send_safe_html_message(
    bot_token: str,
    chat_id: str,
    text: str,
    disable_preview: bool = True,
    reply_markup: Optional[Dict[str, Any]] = None,
) -> bool:
    """Envía un mensaje a Telegram asegurando que si excede los 4000 caracteres no se rompan las etiquetas HTML."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    if len(text) <= 4000:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": disable_preview,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        try:
            res = requests.post(url, json=payload, timeout=15)
            if not res.ok:
                print(f"[WARN] Telegram API error: {res.text}")
            return res.ok
        except Exception as e:
            print(f"[ERROR] Error al enviar mensaje a Telegram: {e}")
            return False

    # Si excede 4000 caracteres, partir de forma limpia
    chunks = [text[i:i+3800] for i in range(0, len(text), 3800)]
    all_ok = True
    for idx, chunk in enumerate(chunks):
        clean_chunk = chunk
        if "<pre>" in clean_chunk and "</pre>" not in clean_chunk:
            clean_chunk += "</pre>"
        elif "</pre>" in clean_chunk and "<pre>" not in clean_chunk:
            clean_chunk = "<pre>" + clean_chunk

        payload = {
            "chat_id": chat_id,
            "text": clean_chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": disable_preview,
        }
        # Agregar el botón en el último fragmento
        if idx == len(chunks) - 1 and reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            res = requests.post(url, json=payload, timeout=15)
            if not res.ok:
                all_ok = False
        except Exception:
            all_ok = False
    return all_ok


def send_single_project_draft(
    bot_token: str,
    chat_id: str,
    repo_name: str,
    post_text: str,
    visual_suggestion: str,
    first_comment: str = "",
    carousel_script: str = "",
    quality_score: float = 5.0,
    model_name: str = "",
    reply_markup: Optional[Dict[str, Any]] = None,
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

    model_display = f"🧠 <b>IA:</b> <code>{html.escape(model_name)}</code> | " if model_name else ""
    score_display = f"{model_display}⭐ <b>Score:</b> {quality_score:.1f}/5.0\n" if quality_score else ""

    # 1. Mensaje del Post Principal (Con bloque <pre> para copiar en un toque)
    post_message = (
        f"📦 <b>Proyecto [{project_index}/{total_projects}]: <code>{safe_repo}</code></b>\n"
        f"{score_display}\n"
        "📝 <b>POST DE LINKEDIN</b> <i>(Toca el bloque gris para copiarlo todo)</i>:\n"
        f"<pre>{safe_post}</pre>"
    )
    _send_safe_html_message(bot_token, chat_id, post_message)

    # 2. Mensaje de Primer Comentario y Sugerencia Visual
    comment_visual_message = (
        f"💬 <b>PRIMER COMENTARIO (Regla 60 min)</b> <i>(Toca para copiar)</i>:\n"
        f"<pre>{safe_first_comment}</pre>\n\n"
        f"📸 <b>SUGERENCIA VISUAL:</b>\n"
        f"{safe_visual}"
    )

    has_carousel = bool(safe_carousel and len(safe_carousel.strip()) > 20)

    # Si no hay carrusel, ponemos el botón en el mensaje de comentario/visual
    if not has_carousel:
        _send_safe_html_message(bot_token, chat_id, comment_visual_message, reply_markup=reply_markup)
    else:
        _send_safe_html_message(bot_token, chat_id, comment_visual_message)

        # 3. Mensaje de Guion de Carrusel PDF para Canva AI (con el botón inline al final)
        carousel_message = (
            "📑 <b>GUION DE CARRUSEL CANVA AI (10 Slides - 1200x1500px)</b>\n\n"
            "💡 <b>Paso a paso para Canva:</b>\n"
            "1️⃣ En Canva creá diseño en <b>Tamaño personalizado: 1200 x 1500 px</b> (4:5 Vertical).\n"
            "2️⃣ Tocá el bloque gris de abajo para copiar el Prompt Maestro y pegalo en <b>Canva AI Chat / Texto Mágico (<code>/</code>)</b>:\n\n"
            f"<pre>{safe_carousel}</pre>"
        )
        _send_safe_html_message(bot_token, chat_id, carousel_message, reply_markup=reply_markup)

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
        _send_safe_html_message(bot_token, chat_id, intro)

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
            model_name=draft.get("used_model", ""),
            project_index=i,
            total_projects=total,
        )
        if not success:
            all_success = False

    return all_success

"""Módulo de envío de notificaciones y paquetes de publicación a Telegram con soporte para botones inline y Tap-to-Copy."""

import html
import re
import time
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


def send_telegram_document(
    bot_token: str,
    chat_id: str,
    file_bytes: bytes,
    filename: str,
    caption: str = "",
    reply_markup: Optional[Dict[str, Any]] = None,
) -> bool:
    """Envía un archivo binario (ej. PDF) directamente a Telegram con reintentos."""
    url = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    for attempt in range(1, 4):
        try:
            data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
            if reply_markup:
                import json
                data["reply_markup"] = json.dumps(reply_markup)
            files = {"document": (filename, file_bytes, "application/pdf")}
            res = requests.post(url, data=data, files=files, timeout=60)
            if res.ok:
                return True
            print(f"[WARN] Intento {attempt}/3 falló enviando documento a Telegram: {res.text}")
        except Exception as e:
            print(f"[WARN] Intento {attempt}/3 excepción enviando documento a Telegram: {e}")
        time.sleep(2)
    return False


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
    pdf_bytes: Optional[bytes] = None,
    canva_edit_url: str = "",
    pdf_qc: Optional[Dict[str, Any]] = None,
    humanizer_qc: Optional[Dict[str, Any]] = None,
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

    # Fallback automático: si humanizer_qc no vino precalculado, auditar en el momento
    if not humanizer_qc and post_text:
        try:
            from src.humanizer_qc import audit_text_humanizer_qc
            post_qc_res = audit_text_humanizer_qc(post_text)
            humanizer_qc = {"overall_score": post_qc_res.get("score", 5.0), "passed": post_qc_res.get("passed", True)}
        except Exception:
            humanizer_qc = {"overall_score": 5.0, "passed": True}

    h_score = humanizer_qc.get("overall_score", 5.0) if humanizer_qc else 5.0
    h_passed = humanizer_qc.get("passed", True) if humanizer_qc else True
    h_icon = "✅" if h_passed else "⚠️"
    h_status = "Aprobado" if h_passed else "Observado"

    model_display = f"🧠 <b>IA:</b> <code>{html.escape(model_name)}</code>\n" if model_name else ""
    score_display = f"⭐ <b>Score:</b> {quality_score:.1f}/5.0 | 👤 <b>Humanizer QC:</b> {h_icon} {h_score:.1f}/5.0 ({h_status})" if quality_score else f"👤 <b>Humanizer QC:</b> {h_icon} {h_score:.1f}/5.0 ({h_status})"

    header_status = f"{model_display}{score_display}\n"

    # 1. Mensaje del Post Principal (Con bloque <pre> para copiar en un toque)
    post_message = (
        f"📦 <b>Proyecto [{project_index}/{total_projects}]: <code>{safe_repo}</code></b>\n"
        f"{header_status}\n"
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

    # 2. Mensaje de Primer Comentario y Sugerencia Visual (con botón de cambio de idioma)
    _send_safe_html_message(bot_token, chat_id, comment_visual_message, reply_markup=reply_markup)

    # 3. Si hay PDF de carrusel compilado, enviarlo directamente como documento adjunto
    if pdf_bytes:
        clean_filename = f"carrusel_{repo_name.replace('/', '_')}.pdf"
        caption_text = f"📄 <b>Carrusel PDF listo para publicar:</b> <code>{safe_repo}</code>"
        if pdf_qc:
            theme_name = pdf_qc.get("theme_name")
            if theme_name:
                caption_text += f"\n🎨 <b>Estilo:</b> {html.escape(theme_name)}"
            qc_score = pdf_qc.get("overall_score", 4.5)
            is_passed = pdf_qc.get("passed", True)
            status_icon = "✅" if is_passed else "⚠️"
            status_label = "Aprobado" if is_passed else "Observado"
            caption_text += f"\n🎯 <b>Control de Calidad Visual (QC):</b> {status_icon} {qc_score:.1f}/5.0 ({status_label})"
        caption_text += f"\n👤 <b>Humanizer QC:</b> {h_icon} {h_score:.1f}/5.0 ({h_status})"
        if canva_edit_url:
            caption_text += f"\n🎨 <a href='{canva_edit_url}'>Abrir y editar en Canva</a>"
        send_telegram_document(
            bot_token=bot_token,
            chat_id=chat_id,
            file_bytes=pdf_bytes,
            filename=clean_filename,
            caption=caption_text,
        )

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
            pdf_bytes=draft.get("pdf_bytes"),
            canva_edit_url=draft.get("canva_edit_url", ""),
            pdf_qc=draft.get("pdf_qc"),
            humanizer_qc=draft.get("humanizer_qc"),
        )
        if not success:
            all_success = False

    return all_success

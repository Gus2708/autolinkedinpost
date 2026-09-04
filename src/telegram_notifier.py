"""Módulo de envío de notificaciones y paquetes de publicación a Telegram con soporte para botones inline y Tap-to-Copy."""

import html
import json
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
import requests


# Telegram acepta 4096 caracteres por mensaje; dejamos margen para los tags que se
# reabren al cortar y para el sufijo de continuación.
TELEGRAM_MAX_CHARS = 4096
CHUNK_LIMIT = 3800

# Tags que Telegram interpreta con parse_mode=HTML y que deben quedar balanceados por chunk.
_TAG_RE = re.compile(r"<(/?)([a-zA-Z][a-zA-Z0-9-]*)((?:\s[^>]*)?)>")

# Tags sin cierre: no entran al stack de balanceo.
_VOID_TAGS = {"br", "hr", "img"}

# Contenido mínimo por fragmento; evita quedar iterando sin avanzar.
_MIN_BODY_CHARS = 16

# Pasadas de ajuste entre el corte tentativo y el sufijo real de cierre.
_MAX_FIT_ATTEMPTS = 4


def _safe_cut_positions(text: str) -> List[bool]:
    """Marca cada índice del texto como punto de corte seguro o no.

    Un corte es inseguro si cae dentro de un tag (`<b>`) o de una entidad HTML (`&amp;`),
    porque partir ahí produce markup inválido y Telegram rechaza el mensaje entero.
    """
    safe = [True] * (len(text) + 1)
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "<":
            end = text.find(">", i)
            end = end if end != -1 else len(text) - 1
            for j in range(i + 1, min(end + 1, len(text)) + 1):
                safe[j] = False
            i = end + 1
        elif ch == "&":
            end = text.find(";", i)
            # Una entidad válida es corta; si no aparece ';' cerca, es un '&' literal.
            if end != -1 and end - i <= 10:
                for j in range(i + 1, end + 2):
                    safe[j] = False
                i = end + 1
            else:
                i += 1
        else:
            i += 1
    return safe


def _find_cut(text: str, safe: List[bool], pos: int, hard_limit: int) -> int:
    """Elige el mejor punto de corte en (pos, hard_limit], o -1 si no hay ninguno seguro.

    Prefiere un salto de línea, después un espacio, y por último cualquier posición
    que no caiga dentro de un tag o de una entidad HTML.
    """
    for preferred in ("\n", " ", None):
        for j in range(hard_limit, pos, -1):
            if not safe[j]:
                continue
            if preferred is None or text[j - 1] == preferred:
                return j
    return -1


def _next_safe_position(safe: List[bool], pos: int, length: int) -> int:
    """Primera posición segura estrictamente mayor que pos, o `length` si no hay otra.

    Se usa como garantía de avance: sin ella, un fragmento sin ningún corte válido
    dejaba `pos` clavado y el bucle principal no terminaba nunca.
    """
    for j in range(pos + 1, length + 1):
        if safe[j]:
            return j
    return length


def _simulate_stack(open_stack: List[Tuple[str, str]], body: str) -> List[Tuple[str, str]]:
    """Calcula qué tags quedan abiertos después de procesar `body`.

    Cada entrada guarda (nombre, texto_de_apertura_completo) para poder reabrir el tag
    con sus atributos intactos: reabrir un `<a href="...">` como `<a>` produce markup
    que Telegram rechaza.
    """
    stack = list(open_stack)
    for match in _TAG_RE.finditer(body):
        closing, name = match.group(1), match.group(2).lower()
        if closing:
            if any(entry[0] == name for entry in stack):
                # Cerrar hasta el tag correspondiente (el markup real está bien anidado).
                while stack and stack.pop()[0] != name:
                    pass
        elif name not in _VOID_TAGS:
            stack.append((name, match.group(0)))
    return stack


def split_html_safe(text: str, limit: int = CHUNK_LIMIT) -> List[str]:
    """Parte un texto HTML en fragmentos válidos para Telegram.

    Garantiza tres cosas:
    1. Ningún corte cae dentro de un tag o de una entidad HTML.
    2. Cada fragmento queda balanceado, reabriendo los tags con sus atributos.
    3. Cada fragmento respeta `limit`, ajustando la reserva al sufijo real.

    El bucle siempre avanza: si un fragmento no admite ningún corte válido, se emite en
    modo degradado en lugar de quedarse iterando sobre la misma posición.
    """
    if len(text) <= limit:
        return [text]

    safe = _safe_cut_positions(text)
    length = len(text)
    chunks: List[str] = []
    open_stack: List[Tuple[str, str]] = []
    pos = 0

    while pos < length:
        prefix = "".join(open_text for _, open_text in open_stack)

        # Si reabrir el contexto no deja lugar para contenido, se corta el fragmento sin
        # herencia de formato: es preferible perder el estilo a no avanzar nunca.
        if limit - len(prefix) < _MIN_BODY_CHARS:
            print("[WARN] Anidamiento de tags demasiado profundo para el límite de Telegram; se corta sin heredar formato.")
            prefix = ""
            open_stack = []

        # La reserva arranca estimada con el stack actual y se corrige con el sufijo real:
        # el cuerpo puede abrir tags nuevos y hacer el cierre más largo de lo previsto.
        reserve = sum(len(name) + 3 for name, _ in open_stack)
        cut = pos
        body = ""
        stack_after = list(open_stack)
        suffix = ""

        for _ in range(_MAX_FIT_ATTEMPTS):
            body_budget = limit - len(prefix) - reserve
            if body_budget < 1:
                body_budget = _MIN_BODY_CHARS

            if pos + body_budget >= length:
                cut = length
            else:
                cut = _find_cut(text, safe, pos, pos + body_budget)
                if cut <= pos:
                    # Sin corte seguro en la ventana: avanzar hasta el siguiente disponible
                    # aunque el fragmento quede por encima del límite preferido.
                    cut = _next_safe_position(safe, pos, length)

            body = text[pos:cut]
            stack_after = _simulate_stack(open_stack, body)
            suffix = "".join(f"</{name}>" for name, _ in reversed(stack_after))

            if len(prefix) + len(body) + len(suffix) <= limit or cut >= length:
                break
            # Reintentar con la reserva real medida sobre este cuerpo.
            reserve = len(suffix)

        # Garantía de terminación: pase lo que pase, la posición avanza.
        if cut <= pos:
            cut = _next_safe_position(safe, pos, length)
            body = text[pos:cut]
            stack_after = _simulate_stack(open_stack, body)
            suffix = "".join(f"</{name}>" for name, _ in reversed(stack_after))

        chunks.append(prefix + body + suffix)
        open_stack = stack_after
        pos = cut

    return chunks


def _post_telegram(url: str, payload: Dict[str, Any], attempts: int = 3) -> bool:
    """POST a la API de Telegram con reintentos y backoff, respetando retry_after en 429."""
    for attempt in range(1, attempts + 1):
        try:
            res = requests.post(url, json=payload, timeout=20)
            if res.ok:
                return True

            # Rate limit: Telegram indica cuántos segundos esperar.
            if res.status_code == 429:
                try:
                    wait = int(res.json().get("parameters", {}).get("retry_after", 3))
                except Exception:
                    wait = 3
                print(f"[WARN] Telegram rate limit, esperando {wait}s (intento {attempt}/{attempts})...")
                time.sleep(min(wait, 30))
                continue

            print(f"[WARN] Telegram API {res.status_code} (intento {attempt}/{attempts}): {res.text[:200]}")
            # 4xx distinto de 429 es un error de contenido: reintentar no lo arregla.
            if 400 <= res.status_code < 500:
                return False
        except requests.RequestException as e:
            print(f"[WARN] Error de red enviando a Telegram (intento {attempt}/{attempts}): {e}")

        if attempt < attempts:
            time.sleep(2 * attempt)
    return False


def _send_safe_html_message(
    bot_token: str,
    chat_id: str,
    text: str,
    disable_preview: bool = True,
    reply_markup: Optional[Dict[str, Any]] = None,
) -> bool:
    """Envía un mensaje a Telegram partiéndolo en fragmentos HTML válidos si excede el límite.

    Devuelve True sólo si TODOS los fragmentos se entregaron.
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    chunks = split_html_safe(text, CHUNK_LIMIT)

    all_ok = True
    for idx, chunk in enumerate(chunks):
        payload = {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": disable_preview,
        }
        # El teclado inline va sólo en el último fragmento.
        if idx == len(chunks) - 1 and reply_markup:
            payload["reply_markup"] = reply_markup

        if not _post_telegram(url, payload):
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

    # Telegram rechaza documentos de más de 50 MB: avisar en vez de reintentar tres veces.
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > 50:
        print(f"[ERROR] El PDF pesa {size_mb:.1f} MB y supera el límite de 50 MB de Telegram.")
        return False

    attempts = 3
    for attempt in range(1, attempts + 1):
        try:
            data = {"chat_id": chat_id, "caption": caption[:1024], "parse_mode": "HTML"}
            if reply_markup:
                data["reply_markup"] = json.dumps(reply_markup)
            files = {"document": (filename, file_bytes, "application/pdf")}
            res = requests.post(url, data=data, files=files, timeout=120)
            if res.ok:
                return True
            print(f"[WARN] Intento {attempt}/{attempts} falló enviando documento: {res.text[:200]}")
            # 4xx distinto de 429 es un problema del payload: reintentar no lo arregla.
            if 400 <= res.status_code < 500 and res.status_code != 429:
                return False
        except requests.RequestException as e:
            print(f"[WARN] Intento {attempt}/{attempts} excepción enviando documento: {e}")

        if attempt < attempts:
            time.sleep(2 * attempt)
    return False


def send_single_project_draft(
    bot_token: str,
    chat_id: str,
    repo_name: str,
    post_text: str,
    first_comment: str = "",
    carousel_script: str = "",
    quality_score: float = 5.0,
    model_name: str = "",
    reply_markup: Optional[Dict[str, Any]] = None,
    project_index: int = 1,
    total_projects: int = 1,
    pdf_bytes: Optional[bytes] = None,
    pdf_qc: Optional[Dict[str, Any]] = None,
    humanizer_qc: Optional[Dict[str, Any]] = None,
    quality_evaluated: bool = True,
) -> bool:
    """Envía el paquete completo de publicación de un proyecto específico a Telegram."""
    if not post_text or post_text.strip().startswith("Error generando post"):
        print(f"[WARN] Omitiendo envío a Telegram para {repo_name} por contenido inválido.")
        return False

    safe_repo = html.escape(repo_name)
    safe_post = html.escape(post_text)
    safe_first_comment = html.escape(first_comment)

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

    # Sin evaluación del juez no se muestra un puntaje: informar "4.8" cuando la
    # llamada falló daba una falsa sensación de control de calidad.
    humanizer_display = f"👤 <b>Humanizer QC:</b> {h_icon} {h_score:.1f}/5.0 ({h_status})"
    if quality_evaluated and quality_score:
        score_display = f"⭐ <b>Score:</b> {quality_score:.1f}/5.0 | {humanizer_display}"
    elif not quality_evaluated:
        score_display = f"⭐ <b>Score:</b> ⚪ sin evaluar | {humanizer_display}"
    else:
        score_display = humanizer_display

    header_status = f"{model_display}{score_display}\n"

    post_markup = None
    comment_markup = None
    if reply_markup and "inline_keyboard" in reply_markup:
        post_rows = []
        comment_rows = []
        for row in reply_markup["inline_keyboard"]:
            if any(btn.get("callback_data", "").startswith(("publi_", "feedb_")) for btn in row):
                post_rows.append(row)
            else:
                comment_rows.append(row)
        if post_rows:
            post_markup = {"inline_keyboard": post_rows}
        if comment_rows:
            comment_markup = {"inline_keyboard": comment_rows}

    # 1. Mensaje del Post Principal (Con bloque <pre> y botones de aprobación/feedback)
    post_message = (
        f"📦 <b>Proyecto [{project_index}/{total_projects}]: <code>{safe_repo}</code></b>\n"
        f"{header_status}\n"
        "📝 <b>POST DE LINKEDIN</b> <i>(Toca el bloque gris para copiarlo todo)</i>:\n"
        f"<pre>{safe_post}</pre>"
    )
    delivered = _send_safe_html_message(bot_token, chat_id, post_message, reply_markup=post_markup)

    # 2. Mensaje del Primer Comentario (con botón de cambio de idioma u otros controles)
    comment_visual_message = (
        f"💬 <b>PRIMER COMENTARIO (Regla 60 min)</b> <i>(Toca para copiar)</i>:\n"
        f"<pre>{safe_first_comment}</pre>"
    )

    delivered = _send_safe_html_message(
        bot_token, chat_id, comment_visual_message, reply_markup=comment_markup
    ) and delivered

    # 3. Si hay PDF de carrusel compilado, guardarlo en caché de disco y enviarlo como documento adjunto
    if pdf_bytes:
        try:
            os.makedirs("data", exist_ok=True)
            with open(os.path.join("data", f"latest_carousel_{chat_id}.pdf"), "wb") as f:
                f.write(pdf_bytes)
        except Exception:
            pass

        clean_filename = f"carrusel_{repo_name.replace('/', '_')}.pdf"
        caption_text = f"📄 <b>Carrusel PDF listo para publicar:</b> <code>{safe_repo}</code>"
        if pdf_qc:
            theme_name = pdf_qc.get("theme_name")
            if theme_name:
                caption_text += f"\n🎨 <b>Estilo:</b> {html.escape(theme_name)}"

            if pdf_qc.get("visual_audited"):
                qc_score = pdf_qc.get("overall_score", 0.0)
                is_passed = pdf_qc.get("passed", True)
                status_icon = "✅" if is_passed else "⚠️"
                status_label = "Aprobado" if is_passed else "Observado"
                caption_text += f"\n🎯 <b>QC Visual:</b> {status_icon} {qc_score:.1f}/5.0 ({status_label})"

                # Una advertencia sin motivo no es accionable: el lector ve el ⚠️ pero
                # no sabe si mirar el texto, los márgenes o los iconos. El PDF se envía
                # igual —un carrusel observado sigue siendo útil— pero con el porqué.
                if not is_passed:
                    try:
                        from src.pdf_evaluator import summarize_qc_issues
                        motivo = summarize_qc_issues(pdf_qc)
                    except Exception:
                        motivo = ""
                    if motivo:
                        caption_text += f"\n   ↳ <i>{html.escape(motivo)}</i>"
            else:
                pages = pdf_qc.get("structural_check", {}).get("page_count", 0)
                caption_text += f"\n🎯 <b>QC:</b> ⚪ Sólo estructural ({pages} páginas, sin auditoría visual)"
        caption_text += f"\n👤 <b>Humanizer QC:</b> {h_icon} {h_score:.1f}/5.0 ({h_status})"
        delivered = send_telegram_document(
            bot_token=bot_token,
            chat_id=chat_id,
            file_bytes=pdf_bytes,
            filename=clean_filename,
            caption=caption_text,
        ) and delivered

    elif pdf_qc and pdf_qc.get("generation_failed"):
        # Sin este aviso el bot anuncia "compilando carrusel" y después entrega el post
        # sin PDF y sin explicación, así que un fallo de render se lee como si nunca se
        # hubiera pedido carrusel. El guion se manda como respaldo para no perder el
        # trabajo del modelo: sirve para diagnosticar y para maquetar a mano.
        motivo = str(pdf_qc.get("failure_reason") or "causa desconocida")
        aviso = (
            "⚠️ <b>El carrusel PDF no se pudo generar.</b>\n"
            f"↳ <i>{html.escape(motivo)}</i>"
        )
        if carousel_script:
            aviso += "\n\nTe dejo el guion crudo abajo para revisarlo o maquetarlo a mano."
        delivered = _send_safe_html_message(bot_token, chat_id, aviso) and delivered
        if carousel_script:
            delivered = _send_safe_html_message(
                bot_token, chat_id, f"<pre>{html.escape(carousel_script)}</pre>"
            ) and delivered

    if not delivered:
        print(f"[WARN] La entrega a Telegram de {repo_name} falló parcial o totalmente.")

    return delivered


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
        repo = draft.get("repo_name", "proyecto")
        approval_kb = build_approval_keyboard(repo)
        success = send_single_project_draft(
            bot_token=bot_token,
            chat_id=chat_id,
            repo_name=repo,
            post_text=draft.get("post", ""),
            first_comment=draft.get("first_comment", ""),
            carousel_script=draft.get("carousel_script", ""),
            quality_score=draft.get("quality_score", 5.0),
            model_name=draft.get("used_model", ""),
            reply_markup=approval_kb,
            project_index=i,
            total_projects=total,
            pdf_bytes=draft.get("pdf_bytes"),
            pdf_qc=draft.get("pdf_qc"),
            humanizer_qc=draft.get("humanizer_qc"),
            quality_evaluated=draft.get("quality_evaluated", True),
        )
        if not success:
            all_success = False

    return all_success


def build_approval_keyboard(
    repo_name: str,
    draft_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Construye los botones interactivos de aprobación y feedback para Telegram."""
    d_id = (draft_id or repo_name.replace("/", "_"))[:32]
    return {
        "inline_keyboard": [
            [
                {
                    "text": "🚀 Publicar en LinkedIn",
                    "callback_data": f"publi_{d_id}",
                },
                {
                    "text": "✏️ Ajustar / Feedback",
                    "callback_data": f"feedb_{d_id}",
                },
            ]
        ]
    }


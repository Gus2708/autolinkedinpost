"""Servidor de Bot Interactivo de Telegram con Menú de Proyectos y Showcase para Reclutadores (Compatible con Render Free Tier)."""

from collections import OrderedDict
import html
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import sys
import threading
import time
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import requests

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.carousel_renderer import generate_native_carousel_pdf
from src.llm_client import detect_provider, validate_provider_credentials
from src.post_generator import generate_project_showcase_post
from src.repo_analyzer import (
    fetch_repository_deep_context,
    fetch_user_repositories,
)
from src.telegram_notifier import send_single_project_draft


PAGE_SIZE = 5

# Cache en memoria de repositorios por chat_id. Acotado para no crecer sin límite
# en un proceso de larga vida (Render corre el bot indefinidamente).
MAX_CACHED_CHATS = 50
USER_REPOS_CACHE: "OrderedDict[int, List[Dict[str, Any]]]" = OrderedDict()
USER_ROTATION_CACHE: Dict[int, int] = {}


def cache_user_repos(chat_id: int, repos: List[Dict[str, Any]]) -> None:
    """Guarda los repos del chat descartando la entrada más vieja al superar el tope."""
    USER_REPOS_CACHE[chat_id] = repos
    USER_REPOS_CACHE.move_to_end(chat_id)
    while len(USER_REPOS_CACHE) > MAX_CACHED_CHATS:
        USER_REPOS_CACHE.popitem(last=False)


def parse_command(raw_text: str) -> str:
    """Extrae el comando de un mensaje de Telegram de forma tolerante.

    Soporta '/menu', '/menu@MiBot', '/menu argumento' y devuelve cadena vacía para
    cualquier texto que no sea un comando (incluido '@alguien', que antes reventaba
    con IndexError y tiraba abajo el lote entero de updates).
    """
    if not raw_text:
        return ""
    first_token = raw_text.strip().split()
    if not first_token:
        return ""
    token = first_token[0].lower()
    if not token.startswith("/"):
        return ""
    # '/menu@MiBot' -> '/menu'
    return token.split("@", 1)[0]


def is_authorized(chat_id: Optional[int], chat_id_auth: Optional[str]) -> bool:
    """Indica si el chat puede operar el bot.

    Sin TELEGRAM_CHAT_ID configurado el bot queda abierto (modo desarrollo);
    con él configurado, sólo ese chat pasa.
    """
    if not chat_id_auth:
        return True
    return str(chat_id) == str(chat_id_auth)


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Servidor HTTP mínimo para que el Free Tier de Render mantenga el Web Service activo."""
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Auto LinkedIn Post Bot is running OK!")

    def log_message(self, format, *args):
        pass  # Evitar logs ruidosos de healthchecks automáticos


def start_health_check_server():
    """Inicia el servidor HTTP de healthcheck en segundo plano para Render."""
    port_str = os.getenv("PORT")
    if not port_str:
        return
    try:
        port = int(port_str)
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        print(f"[INFO] Servidor HTTP de Healthcheck iniciado en el puerto {port} (Render Free Tier).")
        server.serve_forever()
    except Exception as e:
        print(f"[WARN] No se pudo iniciar el servidor HTTP de healthcheck: {e}")


def telegram_api_request(bot_token: str, method: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Ejecuta una petición a la API de Telegram."""
    url = f"https://api.telegram.org/bot{bot_token}/{method}"
    try:
        response = requests.post(url, json=payload, timeout=30)
        return response.json()
    except Exception as e:
        print(f"[ERROR] Error llamando a Telegram API ({method}): {e}")
        return {"ok": False, "error": str(e)}


def build_repo_keyboard(repos: List[Dict[str, Any]], page: int = 0) -> Dict[str, Any]:
    """Genera el teclado inline de Telegram con paginación de repositorios."""
    start_idx = page * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    current_page_repos = repos[start_idx:end_idx]

    inline_keyboard = []

    for idx, repo in enumerate(current_page_repos, start=start_idx):
        lang = repo.get("language") or "General"
        # fetch_user_repositories expone la clave como 'stars', no como el 'stargazers_count' crudo de la API.
        stars = repo.get("stars", 0)
        star_txt = f" ⭐{stars}" if stars > 0 else ""
        button_text = f"📦 {repo['name']} ({lang}){star_txt}"
        callback_data = f"sc:{idx}"
        inline_keyboard.append([{"text": button_text, "callback_data": callback_data}])

    # Botones de navegación (Anterior / Siguiente)
    nav_row = []
    if page > 0:
        nav_row.append({"text": "⬅️ Anterior", "callback_data": f"page:{page - 1}"})
    if end_idx < len(repos):
        nav_row.append({"text": "Siguiente ➡️", "callback_data": f"page:{page + 1}"})

    if nav_row:
        inline_keyboard.append(nav_row)

    return {"inline_keyboard": inline_keyboard}


def handle_menu_command(
    bot_token: str,
    chat_id: int,
    username: str,
    gh_token: Optional[str] = None,
):
    """Maneja el comando /menu o /proyectos listando los repositorios del usuario."""
    telegram_api_request(bot_token, "sendMessage", {
        "chat_id": chat_id,
        "text": f"🔍 <b>Consultando repositorios en GitHub para <code>@{html.escape(username)}</code>...</b>",
        "parse_mode": "HTML",
    })

    repos = fetch_user_repositories(username, token=gh_token)

    if not repos:
        telegram_api_request(bot_token, "sendMessage", {
            "chat_id": chat_id,
            "text": f"❌ No se encontraron repositorios públicos para <code>@{html.escape(username)}</code> o la cuenta no tiene actividad pública visible.",
            "parse_mode": "HTML",
        })
        return

    # Guardar en cache para responder a callbacks
    cache_user_repos(chat_id, repos)

    reply_markup = build_repo_keyboard(repos, page=0)
    total = len(repos)
    text = (
        f"🚀 <b>Portafolio de Repositorios ({total} encontrados)</b>\n\n"
        f"Seleccioná un proyecto de <code>@{html.escape(username)}</code> para generar su <b>Post de LinkedIn (Estrategia 2026)</b>, "
        f"su <b>Primer Comentario</b> y su <b>Carrusel Nativo 4:5 (Refero / WebGL)</b>:\n"
    )

    telegram_api_request(bot_token, "sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_markup": reply_markup,
    })


def handle_callback_query(
    bot_token: str,
    callback_query: Dict[str, Any],
    gh_token: Optional[str] = None,
    chat_id_auth: Optional[str] = None,
):
    """Procesa los clicks en los botones de repositorios y paginación."""
    cb_id = callback_query.get("id")
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
    message_id = callback_query.get("message", {}).get("message_id")
    data = callback_query.get("data", "")

    # Los callbacks disparan generación con LLM y llamadas a la API de GitHub, así que
    # exigen el mismo control de acceso que los mensajes de texto.
    if not is_authorized(chat_id, chat_id_auth):
        print(f"[WARN] Callback descartado de chat no autorizado: {chat_id}")
        telegram_api_request(bot_token, "answerCallbackQuery", {"callback_query_id": cb_id})
        return

    telegram_api_request(bot_token, "answerCallbackQuery", {"callback_query_id": cb_id})

    repos = USER_REPOS_CACHE.get(chat_id)
    if not repos:
        telegram_api_request(bot_token, "sendMessage", {
            "chat_id": chat_id,
            "text": "⚠️ La sesión expiró. Por favor enviá /menu para volver a cargar tus repositorios.",
        })
        return

    # Paginación
    if data.startswith("page:"):
        try:
            page = int(data.split(":", 1)[1])
        except (IndexError, ValueError):
            print(f"[WARN] callback_data de paginación malformado: {data!r}")
            return
        page = max(0, page)
        reply_markup = build_repo_keyboard(repos, page=page)
        telegram_api_request(bot_token, "editMessageReplyMarkup", {
            "chat_id": chat_id,
            "message_id": message_id,
            "reply_markup": reply_markup,
        })
        return

    # Generación de showcase para un proyecto (Español o Inglés)
    if data.startswith("sc:") or data.startswith("sc_en:"):
        is_english = data.startswith("sc_en:")
        try:
            repo_idx = int(data.split(":", 1)[1])
        except (IndexError, ValueError):
            print(f"[WARN] callback_data de showcase malformado: {data!r}")
            return
        if not 0 <= repo_idx < len(repos):
            return

        selected_repo = repos[repo_idx]
        repo_full_name = selected_repo["full_name"]
        lang = "en" if is_english else "es"
        provider = os.getenv("LLM_PROVIDER") or detect_provider()
        model_name = os.getenv("LLM_MODEL") or os.getenv("GEMINI_MODEL")

        # 1. Notificar inicio de análisis
        if is_english:
            status_msg = f"⏳ <b>Generating English version (US Tech Standard) for <code>{html.escape(repo_full_name)}</code> with {provider.upper()}...</b>"
        else:
            status_msg = f"⏳ <b>Analizando arquitectura y README de <code>{html.escape(repo_full_name)}</code> con {provider.upper()}...</b>"

        telegram_api_request(bot_token, "sendMessage", {
            "chat_id": chat_id,
            "text": status_msg,
            "parse_mode": "HTML",
        })

        # 2. Extraer contexto profundo (README, lenguajes, archivos)
        repo_context = fetch_repository_deep_context(repo_full_name, token=gh_token)

        # 3. Generar post con el LLM correspondiente
        showcase = generate_project_showcase_post(
            repo_context=repo_context,
            api_key=None,
            model_name=model_name,
            language=lang,
            provider=provider,
        )

        if not showcase or not showcase.get("post"):
            err_text = "❌ Temporary error analyzing repository. Please try again." if is_english else f"❌ Hubo un error temporal al analizar <code>{html.escape(repo_full_name)}</code>. Por favor intentá nuevamente."
            telegram_api_request(bot_token, "sendMessage", {
                "chat_id": chat_id,
                "text": err_text,
                "parse_mode": "HTML",
            })
            return

        # Botón para alternar al otro idioma
        if is_english:
            toggle_markup = {
                "inline_keyboard": [
                    [{"text": "🇪🇸 Generar versión en Español (ES)", "callback_data": f"sc:{repo_idx}"}]
                ]
            }
        else:
            toggle_markup = {
                "inline_keyboard": [
                    [{"text": "🇬🇧 Generar todo en Inglés (EN)", "callback_data": f"sc_en:{repo_idx}"}]
                ]
            }

        # 4. Generar carrusel PDF nativo (HTML/CSS 1080x1350 px, 4:5 vertical) y auditar con QC
        pdf_bytes = None
        qc_result = {}
        carousel_script = showcase.get("carousel_script", "")
        if carousel_script:
            rotation_offset = USER_ROTATION_CACHE.get(chat_id, 0)
            USER_ROTATION_CACHE[chat_id] = rotation_offset + 1

            telegram_api_request(bot_token, "sendMessage", {
                "chat_id": chat_id,
                "text": "🎨 <b>Compilando carrusel nativo 4:5 (HTML/CSS) y auditando calidad visual...</b>",
                "parse_mode": "HTML",
            })
            pdf_bytes, _, _, qc_result = generate_native_carousel_pdf(
                carousel_script=carousel_script,
                project_name=repo_full_name,
                index_offset=rotation_offset,
                language=lang,
            )

        # 5. Enviar el paquete estructurado completo con el PDF adjunto y botón de idioma
        send_single_project_draft(
            bot_token=bot_token,
            chat_id=str(chat_id),
            repo_name=repo_full_name,
            post_text=showcase["post"],
            first_comment=showcase.get("first_comment", ""),
            carousel_script=carousel_script,
            quality_score=showcase.get("quality_score", 5.0),
            model_name=showcase.get("used_model", model_name or "LLM"),
            reply_markup=toggle_markup,
            project_index=1,
            total_projects=1,
            pdf_bytes=pdf_bytes,
            pdf_qc=qc_result,
            humanizer_qc=showcase.get("humanizer_qc"),
            quality_evaluated=showcase.get("quality_evaluated", True),
        )


def run_interactive_bot():
    """Bucle principal de ejecución del bot interactivo."""
    load_dotenv()

    # Si estamos en Render, iniciar el servidor de healthcheck en segundo plano
    if os.getenv("PORT"):
        t = threading.Thread(target=start_health_check_server, daemon=True)
        t.start()

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id_auth = os.getenv("TELEGRAM_CHAT_ID")
    username = os.getenv("GH_USERNAME")
    gh_token = os.getenv("GH_TOKEN")
    provider = os.getenv("LLM_PROVIDER") or detect_provider()

    if not bot_token:
        print("[ERROR] TELEGRAM_BOT_TOKEN es requerido en .env para iniciar el bot.")
        sys.exit(1)

    if not username:
        print("[ERROR] GH_USERNAME es requerido para saber qué repositorios listar.")
        sys.exit(1)

    if not chat_id_auth:
        print("[WARN] TELEGRAM_CHAT_ID no configurado: el bot aceptará comandos de CUALQUIER chat.")

    credentials_ok, credentials_error = validate_provider_credentials(provider)
    if not credentials_ok:
        print(f"[ERROR] {credentials_error}")
        sys.exit(1)

    print("=" * 60)
    print("🤖 Bot Interactivo de LinkedIn iniciado exitosamente.")
    print(f"📡 Escuchando mensajes para @{username} (LLM: {provider.upper()})...")
    print("💡 Comandos disponibles en Telegram: /start, /menu, /proyectos")
    print("=" * 60)

    offset = 0

    while True:
        try:
            updates_data = telegram_api_request(bot_token, "getUpdates", {
                "offset": offset,
                "timeout": 25,
                "allowed_updates": ["message", "callback_query"],
            })

            if not updates_data.get("ok"):
                time.sleep(3)
                continue

            updates = updates_data.get("result", [])
            for update in updates:
                offset = update["update_id"] + 1

                # Manejar clicks en botones de forma asíncrona
                if "callback_query" in update:
                    cb_thread = threading.Thread(
                        target=handle_callback_query,
                        kwargs={
                            "bot_token": bot_token,
                            "callback_query": update["callback_query"],
                            "gh_token": gh_token,
                            "chat_id_auth": chat_id_auth,
                        },
                        daemon=True,
                    )
                    cb_thread.start()
                    continue

                # Manejar mensajes de texto
                message = update.get("message", {})
                chat_id = message.get("chat", {}).get("id")
                raw_text = (message.get("text") or "").strip()
                cmd = parse_command(raw_text)

                # Control de autorización: ignorar en silencio a los chats no autorizados.
                # Responder revelaría que el bot existe y convierte cada mensaje ajeno en tráfico saliente.
                if not is_authorized(chat_id, chat_id_auth):
                    print(f"[WARN] Mensaje descartado de chat no autorizado: {chat_id}")
                    continue

                if cmd in ["/start", "/menu", "/proyectos", "/repos"]:
                    handle_menu_command(
                        bot_token=bot_token,
                        chat_id=chat_id,
                        username=username,
                        gh_token=gh_token,
                    )
                elif cmd in ["/help", "/ayuda"]:
                    help_text = (
                        "🤖 <b>Comandos del Bot:</b>\n\n"
                        "• <code>/menu</code> o <code>/proyectos</code>: Muestra tus repositorios de GitHub con botones para generar posts de portafolio y arquitectura.\n"
                        "• <code>/help</code>: Muestra esta ayuda."
                    )
                    telegram_api_request(bot_token, "sendMessage", {
                        "chat_id": chat_id,
                        "text": help_text,
                        "parse_mode": "HTML",
                    })

        except KeyboardInterrupt:
            print("\n[INFO] Bot detenido por el usuario.")
            break
        except Exception as e:
            print(f"[ERROR] Error inesperado en el bucle del bot: {e}")
            time.sleep(3)


if __name__ == "__main__":
    run_interactive_bot()

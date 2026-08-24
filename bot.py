"""Servidor de Bot Interactivo de Telegram con Menú de Proyectos y Showcase para Reclutadores (Compatible con Render Free Tier)."""

import html
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import sys
import threading
import time
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import requests

from src.post_generator import generate_project_showcase_post
from src.repo_analyzer import (
    fetch_repository_deep_context,
    fetch_user_repositories,
)
from src.telegram_notifier import send_single_project_draft


PAGE_SIZE = 5

# Cache en memoria de repositorios por chat_id
USER_REPOS_CACHE: Dict[int, List[Dict[str, Any]]] = {}


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


def telegram_api_request(bot_token: str, method: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Llama a la API de Telegram con manejo de timeouts."""
    url = f"https://api.telegram.org/bot{bot_token}/{method}"
    try:
        res = requests.post(url, json=payload or {}, timeout=35)
        return res.json()
    except requests.RequestException as e:
        print(f"[ERROR] Error de red en {method}: {e}")
        return {"ok": False, "error": str(e)}


def build_repo_keyboard(repos: List[Dict[str, Any]], page: int = 0) -> Dict[str, Any]:
    """Construye un teclado inline de Telegram con botones para cada repositorio y paginación."""
    total_repos = len(repos)
    start_idx = page * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, total_repos)

    keyboard = []
    for idx in range(start_idx, end_idx):
        repo = repos[idx]
        name = repo.get("name", "repo")
        lang = repo.get("language") or ""
        label = f"📦 {name}" + (f" ({lang})" if lang and lang != "General" else "")
        keyboard.append([{"text": label, "callback_data": f"sc:{idx}"}])

    # Botones de navegación
    nav_row = []
    if page > 0:
        nav_row.append({"text": "⬅️ Anterior", "callback_data": f"page:{page - 1}"})
    if end_idx < total_repos:
        nav_row.append({"text": "Siguiente ➡️", "callback_data": f"page:{page + 1}"})

    if nav_row:
        keyboard.append(nav_row)

    return {"inline_keyboard": keyboard}


def handle_menu_command(bot_token: str, chat_id: int, username: str, gh_token: Optional[str] = None):
    """Maneja el comando /menu o /proyectos listando los repositorios con botones interactivos."""
    telegram_api_request(bot_token, "sendMessage", {
        "chat_id": chat_id,
        "text": f"🔍 <i>Consultando repositorios de GitHub para @{username}...</i>",
        "parse_mode": "HTML",
    })

    repos = fetch_user_repositories(username=username, token=gh_token)
    if not repos:
        telegram_api_request(bot_token, "sendMessage", {
            "chat_id": chat_id,
            "text": "❌ No se encontraron repositorios o hubo un problema al consultar GitHub.",
        })
        return

    USER_REPOS_CACHE[chat_id] = repos

    reply_markup = build_repo_keyboard(repos, page=0)
    text = (
        f"🏛️ <b>Portafolio de Proyectos (@{username})</b>\n\n"
        "Seleccioná un repositorio para que Gemini analice su arquitectura completa, decisiones de ingeniería y redacte un **post de portafolio para LinkedIn (ideal para reclutadores y Tech Leads)**:"
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
    gemini_api_key: str,
    gemini_model: str,
    gh_token: Optional[str] = None,
):
    """Procesa los clicks en los botones de repositorios y paginación."""
    cb_id = callback_query.get("id")
    chat_id = callback_query.get("message", {}).get("chat", {}).get("id")
    message_id = callback_query.get("message", {}).get("message_id")
    data = callback_query.get("data", "")

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
        page = int(data.split(":")[1])
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
        repo_idx = int(data.split(":")[1])
        if repo_idx >= len(repos):
            return

        selected_repo = repos[repo_idx]
        repo_full_name = selected_repo["full_name"]
        lang = "en" if is_english else "es"

        # 1. Notificar inicio de análisis
        if is_english:
            status_msg = f"⏳ <b>Generating English version (US Tech Standard) for <code>{html.escape(repo_full_name)}</code> with Gemini...</b>"
        else:
            status_msg = f"⏳ <b>Analizando arquitectura y README de <code>{html.escape(repo_full_name)}</code> con Gemini...</b>"

        telegram_api_request(bot_token, "sendMessage", {
            "chat_id": chat_id,
            "text": status_msg,
            "parse_mode": "HTML",
        })

        # 2. Extraer contexto profundo (README, lenguajes, archivos)
        repo_context = fetch_repository_deep_context(repo_full_name, token=gh_token)

        # 3. Generar post con Gemini en el idioma correspondiente
        showcase = generate_project_showcase_post(
            repo_context=repo_context,
            api_key=gemini_api_key,
            model_name=gemini_model,
            language=lang,
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

        # 4. Enviar el paquete estructurado completo con el botón de idioma
        send_single_project_draft(
            bot_token=bot_token,
            chat_id=str(chat_id),
            repo_name=repo_full_name,
            post_text=showcase["post"],
            visual_suggestion=showcase.get("visual_suggestion", ""),
            first_comment=showcase.get("first_comment", ""),
            carousel_script=showcase.get("carousel_script", ""),
            quality_score=showcase.get("quality_score", 5.0),
            model_name=showcase.get("used_model", gemini_model),
            reply_markup=toggle_markup,
            project_index=1,
            total_projects=1,
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
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    username = os.getenv("GH_USERNAME", "gus2708")
    gh_token = os.getenv("GH_TOKEN")
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")

    if not bot_token or not gemini_api_key:
        print("[ERROR] TELEGRAM_BOT_TOKEN y GEMINI_API_KEY son requeridos en .env")
        sys.exit(1)

    print("=" * 60)
    print("🤖 Bot Interactivo de LinkedIn iniciado exitosamente.")
    print(f"📡 Escuchando mensajes para @{username}...")
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
                            "gemini_api_key": gemini_api_key,
                            "gemini_model": gemini_model,
                            "gh_token": gh_token,
                        },
                        daemon=True,
                    )
                    cb_thread.start()
                    continue

                # Manejar mensajes de texto
                message = update.get("message", {})
                chat_id = message.get("chat", {}).get("id")
                text = (message.get("text") or "").strip().lower()

                # Control de autorización si está configurado TELEGRAM_CHAT_ID
                if chat_id_auth and str(chat_id) != str(chat_id_auth):
                    telegram_api_request(bot_token, "sendMessage", {
                        "chat_id": chat_id,
                        "text": "⛔ Acceso no autorizado.",
                    })
                    continue

                if text in ["/start", "/menu", "/proyectos", "/repos"]:
                    handle_menu_command(
                        bot_token=bot_token,
                        chat_id=chat_id,
                        username=username,
                        gh_token=gh_token,
                    )
                elif text in ["/help", "/ayuda"]:
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

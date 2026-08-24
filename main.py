"""Punto de entrada principal para el Auto LinkedIn Post Generator (Revisión Diaria y Segmentada)."""

import argparse
import os
import sys
from dotenv import load_dotenv

from src.github_extractor import (
    fetch_recent_github_activity,
    format_commits_for_llm,
)
from src.post_generator import generate_posts_by_project
from src.telegram_notifier import send_telegram_project_drafts


MOCK_ACTIVITY = {
    "empresa/core-api": [
        "feat(auth): migrate token rotation from memory cache to distributed redis cluster with exponential backoff",
        "perf(db): optimize n+1 queries in workspace billing aggregation using eager loading and composite indexes",
        "fix(rate-limit): prevent race conditions in sliding window limiter under high concurrent load"
    ],
    "personal/microservices-toolkit": [
        "refactor(cqrs): implement outbox pattern to guarantee event consistency with kafka",
        "docs(arch): add c4 model diagrams for event-driven payment reconciliation service"
    ]
}


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Revisa actividad diaria en GitHub, genera posts segmentados por proyecto con Gemini y los envía a Telegram."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Imprime los posts y sugerencias en consola sin enviar a Telegram.",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Usa datos de actividad simulados para pruebas locales sin llamar a GitHub API.",
    )
    parser.add_argument(
        "--days",
        type=int,
        default=int(os.getenv("LOOKBACK_DAYS", "1")),
        help="Días hacia atrás para buscar actividad (por defecto 1 para revisión diaria).",
    )
    parser.add_argument(
        "--username",
        type=str,
        default=os.getenv("GH_USERNAME"),
        help="Nombre de usuario de GitHub.",
    )
    args = parser.parse_args()

    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        print("[ERROR] Variable GEMINI_API_KEY no encontrada en el entorno.")
        sys.exit(1)

    model_name = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")

    # 1. Obtener actividad
    if args.mock:
        print("[INFO] Usando datos de actividad simulados (--mock)...")
        activity = MOCK_ACTIVITY
    else:
        username = args.username
        if not username:
            print("[ERROR] GH_USERNAME no configurado ni pasado por argumento.")
            sys.exit(1)
        token = os.getenv("GH_TOKEN")
        print(f"[INFO] Consultando actividad de GitHub para @{username} (últimos {args.days} día(s))...")
        activity = fetch_recent_github_activity(
            username=username,
            token=token,
            lookback_days=args.days,
        )

    if not activity:
        print(f"[INFO] No se encontró actividad técnica relevante en las últimas {args.days * 24} horas. No hay nada nuevo que publicar hoy.")
        sys.exit(0)

    print(f"\n[INFO] Se encontró actividad técnica en {len(activity)} repositorio(s):")
    for repo, commits in activity.items():
        print(f"  • {repo}: {len(commits)} cambio(s) relevante(s)")

    # 2. Generar posts segmentados por cada proyecto
    print(f"\n[INFO] Generando posts segmentados con Gemini ({model_name})...")
    drafts = generate_posts_by_project(
        activity_by_repo=activity,
        api_key=gemini_api_key,
        model_name=model_name,
    )

    for i, draft in enumerate(drafts, start=1):
        print("\n" + "=" * 55)
        print(f"📦 [{i}/{len(drafts)}] PROYECTO: {draft['repo_name']}")
        print("=" * 55)
        print("📝 POST DE LINKEDIN:")
        print(draft["post"])
        print("\n📸 SUGERENCIA VISUAL:")
        print(draft["visual_suggestion"])
        print("=" * 55)

    # 3. Enviar a Telegram
    if args.dry_run:
        print("\n[INFO] Modo --dry-run activado: No se envían mensajes a Telegram.")
    else:
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
        telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID")
        if not telegram_token or not telegram_chat_id:
            print("[WARN] TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID no configurados. Omitiendo envío.")
        else:
            print(f"\n[INFO] Enviando {len(drafts)} borrador(es) individual(es) a Telegram...")
            success = send_telegram_project_drafts(
                bot_token=telegram_token,
                chat_id=telegram_chat_id,
                drafts=drafts,
            )
            if success:
                print("[SUCCESS] ¡Todos los borradores fueron enviados exitosamente a Telegram!")
            else:
                print("[WARN] Algunos borradores no pudieron ser enviados a Telegram.")


if __name__ == "__main__":
    main()

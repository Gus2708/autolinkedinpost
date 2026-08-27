"""Punto de entrada principal para el Auto LinkedIn Post Generator (Revisión Diaria y Segmentada con Multi-LLM)."""

import argparse
import os
import sys
from dotenv import load_dotenv

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.carousel_renderer import generate_native_carousel_pdf
from src.github_extractor import (
    fetch_recent_github_activity,
    format_commits_for_llm,
)
from src.llm_client import detect_provider
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
        description="Revisa actividad diaria en GitHub, genera posts segmentados con cualquier LLM (Gemini, OpenAI, Claude, DeepSeek, etc.) y los envía a Telegram."
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
    parser.add_argument(
        "--provider",
        type=str,
        default=os.getenv("LLM_PROVIDER"),
        help="Proveedor de LLM (gemini, openai, anthropic, deepseek, groq, openrouter, ollama, custom).",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=os.getenv("LLM_MODEL") or os.getenv("GEMINI_MODEL"),
        help="Modelo específico de LLM a utilizar.",
    )
    parser.add_argument(
        "--lang",
        type=str,
        default="es",
        choices=["es", "en"],
        help="Idioma del contenido generado ('es' o 'en').",
    )
    parser.add_argument(
        "--no-carousel",
        action="store_true",
        help="Deshabilita la generación y exportación automática de carruseles PDF nativos.",
    )
    args = parser.parse_args()

    provider = args.provider or detect_provider()
    model_name = args.model

    print(f"[INFO] Proveedor LLM detectado: {provider.upper()}")

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
    print(f"\n[INFO] Generando posts segmentados [{args.lang.upper()}] con {provider.upper()}...")
    drafts = generate_posts_by_project(
        activity_by_repo=activity,
        model_name=model_name,
        language=args.lang,
        provider=provider,
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

    # 2.5 Generar carruseles PDF nativos HTML/CSS y Control de Calidad (QC)
    if not args.no_carousel:
        print("\n[INFO] Compilando carruseles multipagina nativos 4:5 (HTML/CSS) y auditando calidad visual...")
        for draft in drafts:
            script = draft.get("carousel_script")
            repo = draft.get("repo_name", "proyecto")
            if script:
                print(f"  • Renderizando carrusel nativo para {repo}...")
                pdf_bytes, _, _, qc_result = generate_native_carousel_pdf(
                    carousel_script=script,
                    project_name=repo,
                )
                if pdf_bytes:
                    draft["pdf_bytes"] = pdf_bytes
                    draft["pdf_qc"] = qc_result
                    score = qc_result.get("overall_score", 4.5)
                    print(f"    [OK] PDF generado y auditado por QC (Score {score:.1f}/5.0 - {len(pdf_bytes)} bytes)")
                else:
                    print(f"    [WARN] No se pudo exportar PDF para {repo}, se enviará texto.")

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

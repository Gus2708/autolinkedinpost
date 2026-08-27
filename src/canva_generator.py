"""Módulo cliente para Canva MCP (Model Context Protocol).
Permite crear y exportar carruseles multipágina en PDF de forma 100% automatizada.
"""

import asyncio
import json
import os
import shutil
from typing import Any, Dict, Optional, Tuple
import requests

from src.pdf_evaluator import audit_carousel_pdf

import base64
from pathlib import Path

try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False


def restore_canva_tokens_from_env() -> bool:
    """Restaura automáticamente los tokens de Canva desde la variable de entorno CANVA_AUTH_TOKENS (para Render, GitHub Actions o Docker)."""
    token_b64 = os.getenv("CANVA_AUTH_TOKENS", "").strip()
    if not token_b64:
        return False

    try:
        raw_json = base64.b64decode(token_b64.encode("utf-8")).decode("utf-8")
        pkg = json.loads(raw_json)

        mcp_hash = pkg.get("hash") or "67a2071180bfcf76a3985779a9a38813"
        tokens = pkg.get("tokens")
        client_info = pkg.get("client_info")

        if not tokens or not client_info:
            return False

        auth_dir = Path.home() / ".mcp-auth" / "mcp-remote-v1"
        auth_dir.mkdir(parents=True, exist_ok=True)

        tokens_file = auth_dir / f"{mcp_hash}_tokens.json"
        client_info_file = auth_dir / f"{mcp_hash}_client_info.json"

        # Escribir solo si no existen o se actualizó la variable
        tokens_file.write_text(json.dumps(tokens, indent=2), encoding="utf-8")
        client_info_file.write_text(json.dumps(client_info, indent=2), encoding="utf-8")
        return True
    except Exception as e:
        print(f"[WARN] No se pudieron restaurar los tokens de Canva desde CANVA_AUTH_TOKENS: {e}")
        return False


def is_canva_mcp_supported() -> bool:
    """Verifica si el entorno soporta ejecutar Canva MCP (mcp package + npx en PATH) y restaura credenciales si existen."""
    # Restaurar credenciales desde el entorno si se está ejecutando en un servidor desatendido
    restore_canva_tokens_from_env()

    if not MCP_AVAILABLE:
        return False
    return shutil.which("npx") is not None


import fitz


def sanitize_pdf_carousel(pdf_bytes: bytes) -> bytes:
    """Elimina diapositivas de contacto falsas generadas automáticamente por plantillas corporativas de Canva."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        if len(doc) > 1:
            last_page = doc[-1]
            text_lower = last_page.get_text().lower()
            fake_markers = [
                "información de contacto",
                "contact info",
                "reallygreatsite.com",
                "123-456-7890",
                "teléfono",
                "@reallygreatsite",
            ]
            if any(marker in text_lower for marker in fake_markers):
                print(f"[INFO] Eliminando diapositiva de contacto ficticia (Página {len(doc)})...")
                doc.delete_page(len(doc) - 1)
                clean_bytes = doc.tobytes()
                doc.close()
                return clean_bytes
        doc.close()
    except Exception as e:
        print(f"[WARN] Error sanitizando PDF: {e}")
    return pdf_bytes


async def _async_generate_and_export_pdf(
    carousel_script: str,
    project_name: str,
    timeout_seconds: int = 120,
) -> Tuple[Optional[bytes], str, str, Dict[str, Any]]:
    """Genera una presentación con Canva AI, la redimensiona a 4:5 vertical y la exporta a PDF vía Canva MCP."""
    if not is_canva_mcp_supported():
        return None, "", "", {}

    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "mcp-remote@latest", "https://mcp.canva.com/mcp"]
    )

    clean_project = project_name.split("/")[-1].replace("-", " ").title()
    brief_query = (
        f"Presentation Brief:\n"
        f"Title: {clean_project} - Arquitectura e Ingeniería de Software\n"
        f"Topic: Decisiones técnicas reales, arquitectura de software y trade-offs en producción.\n"
        f"Style Guide: Modern Developer / Tech Instagram Carousel style. Clean card layouts with deep dark navy background #0F172A, electric cyan #38BDF8 / #00F5FF accents, and crisp white typography #F8FAFC.\n"
        f"Typography (MANDATORY): ULTRA-MODERN SANS-SERIF ONLY (Inter, Montserrat, Roboto, Helvetica, Archivo Black). FORBIDDEN: NEVER use serif, times, playfair, roman, or editorial fonts. All headings must be bold, clean, and modern sans-serif.\n"
        f"Format: Modern social media vertical cards, high contrast, mobile-first design.\n"
        f"SLIDE 10 / FINAL SLIDE (CRITICAL RULE): Must be a technical debate CTA titled '¿Qué opinás?' or 'Conclusiones y Debate'. FORBIDDEN: NEVER create a 'Contact Info' slide. NEVER include telephone numbers (123-456-7890), fake emails (hello@reallygreatsite.com), or generic social handles.\n\n"
        f"Contenido del carrusel:\n{carousel_script[:3500]}"
    )

    try:
        async with asyncio.timeout(timeout_seconds):
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()

                    # 1. Generar diseño con Canva AI
                    gen_res = await session.call_tool(
                        "generate-design",
                        arguments={
                            "design_type": "presentation",
                            "length": "balanced",
                            "query": brief_query,
                            "user_intent": f"Generar carrusel técnico moderno para {clean_project}",
                        }
                    )

                    if not gen_res.content:
                        return None, "", "", {}

                    data = json.loads(gen_res.content[0].text)
                    job_data = data.get("job", {})
                    job_id = job_data.get("id")
                    candidates = job_data.get("result", {}).get("generated_designs", [])

                    if not job_id or not candidates:
                        return None, "", "", {}

                    cand_id = candidates[0].get("candidate_id")

                    # 2. Convertir candidato a diseño editable
                    save_res = await session.call_tool(
                        "create-design-from-candidate",
                        arguments={
                            "job_id": job_id,
                            "candidate_id": cand_id,
                            "user_intent": f"Guardar carrusel de {clean_project}",
                        }
                    )

                    saved_data = json.loads(save_res.content[0].text)
                    summary = saved_data.get("design_summary", {})
                    design_id = summary.get("id")
                    edit_url = summary.get("urls", {}).get("edit_url", "")

                    if not design_id:
                        return None, edit_url, "", {}

                    # 2.5 Redimensionar a formato vertical 4:5 (1080x1350 px - Estilo Instagram/LinkedIn)
                    target_design_id = design_id
                    try:
                        print(f"  • Redimensionando presentación a formato vertical 4:5 (1080x1350 px)...")
                        resize_res = await session.call_tool(
                            "resize-design",
                            arguments={
                                "design_id": design_id,
                                "design_type": {
                                    "type": "custom",
                                    "width": 1080,
                                    "height": 1350,
                                },
                                "user_intent": f"Redimensionar a formato vertical 4:5 para {clean_project}",
                            }
                        )
                        if resize_res.content:
                            resize_data = json.loads(resize_res.content[0].text)
                            resized_design = resize_data.get("job", {}).get("result", {}).get("design", {})
                            if resized_design.get("id"):
                                target_design_id = resized_design["id"]
                                if resized_design.get("urls", {}).get("edit_url"):
                                    edit_url = resized_design["urls"]["edit_url"]
                    except Exception as e:
                        print(f"[WARN] Error al redimensionar diseño en Canva MCP: {e}")

                    # 3. Exportar el diseño (redimensionado a 4:5) a PDF
                    exp_res = await session.call_tool(
                        "export-design",
                        arguments={
                            "design_id": target_design_id,
                            "format": {"type": "pdf"},
                            "user_intent": "Exportar carrusel vertical 4:5 a PDF",
                        }
                    )

                    exp_data = json.loads(exp_res.content[0].text)
                    urls = exp_data.get("job", {}).get("urls", [])
                    if not urls:
                        return None, edit_url, "", {}

                    pdf_url = urls[0]

                    # 4. Descargar los bytes del PDF
                    pdf_resp = requests.get(pdf_url, timeout=30)
                    if pdf_resp.status_code == 200:
                        pdf_bytes = sanitize_pdf_carousel(pdf_resp.content)
                        # 5. Control de Calidad en dos capas (Estructural + Visual Gemini Vision)
                        print(f"  • Ejecutando Control de Calidad (QC) estructural y visual en todas las láminas...")
                        qc_result = audit_carousel_pdf(pdf_bytes)
                        score = qc_result.get("overall_score", 4.0)
                        passed = qc_result.get("passed", True)
                        if passed:
                            print(f"    [QC APROBADO] Score {score:.1f}/5.0: Diseño vertical 4:5, márgenes y texto validados.")
                        else:
                            print(f"    [QC OBSERVADO] Score {score:.1f}/5.0: {qc_result.get('reasons')}")
                        return pdf_bytes, edit_url, pdf_url, qc_result

                    return None, edit_url, pdf_url, {}

    except Exception as e:
        print(f"[WARN] Error en generación de Canva MCP: {e}")
        return None, "", "", {}


def generate_canva_carousel_pdf(
    carousel_script: str,
    project_name: str,
    timeout_seconds: int = 120,
) -> Tuple[Optional[bytes], str, str, Dict[str, Any]]:
    """Punto de entrada síncrono para generar, auditar y exportar el carrusel con Canva MCP."""
    empty_qc: Dict[str, Any] = {}
    if not os.getenv("ENABLE_CANVA_MCP", "true").lower() in ("true", "1", "yes"):
        return None, "", "", empty_qc
    if not is_canva_mcp_supported():
        return None, "", "", empty_qc

    try:
        return asyncio.run(
            _async_generate_and_export_pdf(
                carousel_script=carousel_script,
                project_name=project_name,
                timeout_seconds=timeout_seconds,
            )
        )
    except Exception as e:
        print(f"[WARN] Excepción al ejecutar Canva MCP: {e}")
        return None, "", "", empty_qc

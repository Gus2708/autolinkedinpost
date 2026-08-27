"""Script de configuración y autenticación Open Source para Canva MCP.

Permite a cualquier desarrollador conectar su cuenta de Canva mediante loopback local
(RFC 8252, sin requerir dominios ni waitlists) y exportar sus credenciales empaquetadas
para desplegar el bot en Render, Railway, Fly.io o GitHub Actions.
"""

import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

CANVA_MCP_URL = "https://mcp.canva.com/mcp"
CANVA_URL_HASH = hashlib.md5(CANVA_MCP_URL.encode()).hexdigest()
MCP_AUTH_DIR = Path.home() / ".mcp-auth" / "mcp-remote-v1"
TOKENS_FILE = MCP_AUTH_DIR / f"{CANVA_URL_HASH}_tokens.json"
CLIENT_INFO_FILE = MCP_AUTH_DIR / f"{CANVA_URL_HASH}_client_info.json"


def check_prerequisites():
    """Verifica que Node.js / npx estén disponibles en el sistema."""
    if not shutil.which("npx"):
        print("❌ [ERROR] 'npx' no fue encontrado en el PATH.")
        print("👉 Por favor instala Node.js (v18+) desde https://nodejs.org/")
        sys.exit(1)


def get_stored_tokens_payload() -> str:
    """Lee los archivos de autenticación de Canva y los empaqueta en una cadena Base64."""
    if not TOKENS_FILE.exists() or not CLIENT_INFO_FILE.exists():
        return ""

    try:
        tokens_data = json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
        client_info_data = json.loads(CLIENT_INFO_FILE.read_text(encoding="utf-8"))

        package = {
            "version": "1.0",
            "url": CANVA_MCP_URL,
            "hash": CANVA_URL_HASH,
            "tokens": tokens_data,
            "client_info": client_info_data,
        }
        json_bytes = json.dumps(package).encode("utf-8")
        return base64.b64encode(json_bytes).decode("utf-8")
    except Exception as e:
        print(f"⚠️ Error empaquetando credenciales: {e}")
        return ""


def run_interactive_login():
    """Inicia el proceso de autenticación interactiva mediante mcp-remote."""
    print("\n🚀 Iniciando handshake OAuth con Canva...")
    print("👉 Se abrirá tu navegador para iniciar sesión y autorizar el acceso.")
    print("⏳ Esperando autorización...\n")

    cmd = ["npx", "-y", "mcp-remote@latest", CANVA_MCP_URL]
    
    # Iniciamos el proceso de mcp-remote para que gestione el login en 127.0.0.1
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Esperar hasta 90 segundos a que aparezca el archivo de tokens
        start_time = time.time()
        while time.time() - start_time < 90:
            if TOKENS_FILE.exists() and CLIENT_INFO_FILE.exists():
                time.sleep(2)  # Dar tiempo a que termine de escribir
                break
            time.sleep(1)

        try:
            proc.terminate()
        except Exception:
            pass

    except Exception as e:
        print(f"❌ Error ejecutando mcp-remote: {e}")


def update_local_env_file(token_str: str):
    """Agrega o actualiza CANVA_AUTH_TOKENS en el archivo .env local."""
    env_path = Path(".env")
    if not env_path.exists():
        return

    content = env_path.read_text(encoding="utf-8")
    if "CANVA_AUTH_TOKENS=" in content:
        lines = []
        for line in content.splitlines():
            if line.startswith("CANVA_AUTH_TOKENS="):
                lines.append(f"CANVA_AUTH_TOKENS={token_str}")
            else:
                lines.append(line)
        env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    else:
        with open(env_path, "a", encoding="utf-8") as f:
            f.write(f"\n# Canva MCP Auth Token\nCANVA_AUTH_TOKENS={token_str}\n")
    print("💾 Variable CANVA_AUTH_TOKENS guardada automáticamente en tu archivo .env local.")


def main():
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 65)
    print("🎨 Auto LinkedIn Post - Asistente de Autenticación Canva MCP")
    print("=" * 65)

    check_prerequisites()

    token_payload = get_stored_tokens_payload()

    if not token_payload:
        run_interactive_login()
        token_payload = get_stored_tokens_payload()

    if not token_payload:
        print("❌ No se detectó la autorización en el tiempo establecido.")
        print("👉 Por favor intentá nuevamente ejecutando: python setup_canva.py")
        sys.exit(1)

    print("\n✅ ¡AUTENTICACIÓN EXITOSA CON CANVA!")
    print("-" * 65)
    print("📋 Para desplegar tu bot en la nube (Render, Railway, GitHub Actions):")
    print("Copia el siguiente valor y pégalo como variable de entorno o Secret")
    print("con el nombre 'CANVA_AUTH_TOKENS':\n")
    print(f"CANVA_AUTH_TOKENS={token_payload}\n")
    print("-" * 65)

    update_local_env_file(token_payload)

    print("\n🎉 ¡Listo! Tu bot ya puede generar y exportar carruseles en cualquier servidor.")
    print("=" * 65)


if __name__ == "__main__":
    main()

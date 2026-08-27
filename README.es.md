# 🚀 AutoLinkedInPost — Senior Engineering Content Engine (Edición Multi-LLM 2026)

[🇺🇸 English Version](README.md) | [🇪🇸 Versión en Español](README.es.md)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Multi-LLM Ready](https://img.shields.io/badge/AI-Gemini%20%7C%20Claude%20%7C%20OpenAI%20%7C%20DeepSeek%20%7C%20Groq%20%7C%20Ollama-purple.svg)](https://github.com/Gus2708/autolinkedinpost)
[![Render Free 24/7](https://img.shields.io/badge/Deploy-Render%20Cloud-success.svg)](https://render.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**AutoLinkedInPost** es un sistema de ingeniería autónomo diseñado para desarrolladores senior, tech leads y fundadores técnicos que buscan posicionar su autoridad técnica frente a reclutadores internacionales y Engineering Managers en LinkedIn.

El sistema audita automáticamente tu actividad en GitHub, extrae decisiones de arquitectura reales y genera paquetes de publicación optimizados para el **Interest Graph de LinkedIn 2026** (Mobile-First, ganchos con corte de 220 caracteres, CTAs de guardado, guiones de carruseles de 10 diapositivas para Canva AI y primer comentario limpio), todo validado mediante un **Quality Gate autónomo (LLM-as-a-Judge)** con política de **Cero Alucinación** y soporte universal para **múltiples proveedores de Inteligencia Artificial**.

---

## 🏛️ Arquitectura del Sistema

```text
               ┌────────────────────────────────────────────────────────┐
               │              GitHub Repository / Activity              │
               │   (Commits, PRs, Tree Structure, README, Tech Stack)   │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │           1. GitHub Extractor & Deep Analyzer          │
               │     • Filtra commits triviales (docs, merges, typos)   │
               │     • Extrae contexto arquitectónico y archivos clave  │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │         2. Multi-LLM Engine (Provider Pattern)         │
               │     • Gemini 3.7 / Claude 3.7 / GPT-4o / DeepSeek /    │
               │       Groq / OpenRouter / Ollama (Modelos Locales)     │
               │     • 1ª Persona Singular ("Diseñé", "Implementé")     │
               │     • Formato Mobile-First (Párrafos de 2 líneas)      │
               │     • Guion de Carrusel 10 Slides (4:5 - 1200x1500px)  │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │         3. LLM-as-a-Judge Quality Gate (Rúbrica 1-5)   │
               │     • Factual Grounding (Veracidad absoluta y código)  │
               │     • Hook Strength (< 220 chars antes de 'Ver más')   │
               │     • Mobile Readability & Save/CTA Factor             │
               │     └─► Si Score < 4.0 ──► Bucle de Auto-Refinamiento  │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │           4. Telegram Dispatcher & Interactive Bot     │
               │     • Bloques nativos monospaced "Tap-to-Copy" (<pre>) │
               │     • Paginación interactiva de repositorios           │
               │     • Switch Bilingüe instantáneo (Español ⇄ English)  │
               │     • Hilos concurrentes (Zero-blocking)               │
               └────────────────────────────────────────────────────────┘
```

---

## 🧠 Arquitectura Multi-LLM (Provider Pattern)

El motor de IA está completamente desacoplado mediante un adaptador agnóstico en [`src/llm_client.py`](file:///g:/Projects/autolinkedinpost/src/llm_client.py), permitiéndote intercambiar proveedores y modelos simplemente cambiando variables de entorno:

| Proveedor | `LLM_PROVIDER` | Variable de API Key | Modelos Recomendados |
|---|---|---|---|
| **Google Gemini** *(Default)* | `gemini` | `GEMINI_API_KEY` | `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash` |
| **Anthropic Claude** | `anthropic` | `ANTHROPIC_API_KEY` | `claude-3-7-sonnet-20250219`, `claude-3-5-sonnet` |
| **OpenAI** | `openai` | `OPENAI_API_KEY` | `gpt-4o`, `gpt-4o-mini`, `o3-mini` |
| **DeepSeek** | `deepseek` | `DEEPSEEK_API_KEY` | `deepseek-chat`, `deepseek-reasoner` |
| **Groq** *(Inferencia ultra rápida)* | `groq` | `GROQ_API_KEY` | `llama-3.3-70b-versatile`, `mixtral-8x7b-32768` |
| **OpenRouter** | `openrouter` | `OPENROUTER_API_KEY` | `anthropic/claude-3.7-sonnet`, `meta-llama/llama-3.3-70b-instruct` |
| **Ollama** *(Modelos Locales / Privados)* | `ollama` | `OLLAMA_BASE_URL` | `llama3.2`, `mistral`, `qwen2.5` |
| **Custom OpenAI-Compatible** | `custom` | `CUSTOM_LLM_API_KEY` | Endpoint en `CUSTOM_LLM_BASE_URL` (vLLM, LMStudio) |

> [!TIP]
> **Auto-Detección Heurística:** Si no defines `LLM_PROVIDER`, el sistema detecta automáticamente el proveedor según la API key que tengas configurada en tu entorno.

---

## ✨ Características Principales

### 🎯 1. Estrategia Algorítmica LinkedIn 2026
- **Ganchos de Alto Impacto (< 220 caracteres):** Tensión de ingeniería o contraste técnico en las primeras 2 líneas para forzar el clic en *"Ver más"*.
- **Mobile-First Real:** Párrafos de máximo 2 a 3 líneas con espacios en blanco obligatorios para lectura fluida en pantallas móviles.
- **CTAs de Guardado (Saves > Likes):** Llamados a la acción diseñados para multiplicar el alcance un 60% en el algoritmo.
- **Regla del Primer Comentario (60 min):** Publicaciones 100% limpias de enlaces externos para evitar la penalización del 50% de alcance orgánico; el enlace al repositorio va formateado en el comentario semilla.

### 🛡️ 2. Veracidad Absoluta y Cero Alucinaciones (Strict Grounding)
- **100% Factual:** Prohibido inventar métricas ficticias, caídas de producción imaginarias o empresas falsas.
- **Autoridad de Código:** Si no hay métricas numéricas en el README, el post se enfoca en el problema de ingeniería real, modularidad, patrones de diseño (RAG, Outbox, CQRS, Caching) y trade-offs asumidos.

### 📑 3. Motor Nativo de Carruseles HTML/CSS a PDF (1080x1350 px)
- **Formato Vertical 4:5 Nativo (1080 x 1350 px):** Ocupa 35% más de pantalla móvil que las imágenes cuadradas o 16:9 de presentaciones.
- **Estética Glassmorphism Dark Tech:** Diseño moderno para desarrolladores (fondo #0B0F19, acentos cian #38BDF8, resplandores #6366F1 y textos de alto contraste #F8FAFC).
- **Layout Responsivo con Flexbox:** Tipografía fluida y tarjetas que se auto-ajustan dinámicamente si el título tiene 1, 2 o 3 líneas, eliminando colisiones y cortes de palabras.
- **Tipografía Integrada de Google Fonts:** *Plus Jakarta Sans* para lectura limpia y *JetBrains Mono* para bloques de código y contadores.
- **Cero Dependencias de APIs Externas:** Renderiza localmente en ~2 segundos con Playwright Chromium sin tokens de diseño que venzan.
- **Control de Calidad Visual Automatizado (Gemini Vision):** Audita la relación de aspecto, márgenes y jerarquía tipográfica antes del envío a Telegram.

### 🌐 4. Generación Bilingüe Instantánea (ES / EN)
- Botón interactivo inline en Telegram (`🇬🇧 Generar todo en Inglés` / `🇪🇸 Generar en Español`) para traducir y adaptar el post completo, primer comentario y guion al estándar **US Tech Professional**.

### 📱 5. UX Móvil con Bloques "Tap-to-Copy"
- Toda la salida en Telegram se entrega en bloques de código monospaced `<pre>`. Con **un solo toque en la pantalla de tu celular**, copiás el texto limpio directamente al portapapeles sin arrastrar títulos, emojis ni metadatos.

---

## 🚀 Inicio Rápido e Instalación

### 1. Clonar el repositorio y crear entorno virtual
```bash
git clone https://github.com/Gus2708/autolinkedinpost.git
cd autolinkedinpost
python -m venv .venv
# En Windows:
.venv\Scripts\activate
# En Linux/macOS:
source .venv/bin/activate
```

### 2. Instalar dependencias y motor de navegador
```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Configurar variables de entorno
Copia el archivo de ejemplo:
```bash
cp .env.example .env
```
Edita tu `.env` con el proveedor de IA y credenciales que prefieras:
```env
# Proveedor de IA (gemini, openai, anthropic, deepseek, groq, openrouter, ollama)
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.7-flash

# API Key del proveedor elegido
GEMINI_API_KEY="tu_gemini_api_key"
# O si usas Anthropic: ANTHROPIC_API_KEY="sk-ant-..."
# O si usas OpenAI: OPENAI_API_KEY="sk-..."
# O si usas DeepSeek: DEEPSEEK_API_KEY="sk-..."

# Telegram Bot
TELEGRAM_BOT_TOKEN="tu_token_de_botfather"
TELEGRAM_CHAT_ID="tu_id_de_telegram"

# GitHub
GH_USERNAME="tu_usuario_github"
GH_TOKEN=""  # Opcional (PAT de GitHub si deseas analizar repositorios privados)
LOOKBACK_DAYS=1
PYTHONIOENCODING=utf-8
```

---

## 🛠️ Modos de Uso

### Modo 1: Bot Interactivo en Telegram (Recomendado)
Ejecuta el bot para consultar tus repositorios y generar showcases bajo demanda desde tu celular:
```bash
python bot.py
```
1. Abre tu bot en Telegram y envía `/menu` o `/proyectos`.
2. Selecciona cualquier repositorio de la lista interactiva.
3. Recibe en segundos:
   - 📝 **Post de LinkedIn** (listo para copiar con 1 toque).
   - 💬 **Primer Comentario** (con el link limpio al repo).
   - 📸 **Sugerencia Visual** (diagrama C4 / arquitectura).
   - 📑 **Guion de Carrusel de 10 Slides + Prompt para Canva**.
   - 🇬🇧 **Botón interactivo para alternar a Inglés**.

### Modo 2: Revisión Diaria por CLI
Revisa la actividad de commits de las últimas 24 horas con el LLM configurado y despacha los borradores a Telegram:
```bash
# Ejecutar revisión diaria con el LLM por defecto
python main.py

# Ejecutar especificando un LLM o modelo particular
python main.py --provider openai --model gpt-4o
python main.py --provider anthropic --model claude-3-7-sonnet-20250219
python main.py --provider deepseek --model deepseek-chat

# Generar directamente en inglés
python main.py --lang en

# Revisar los últimos 7 días
python main.py --days 7

# Probar localmente con datos simulados sin enviar a Telegram
python main.py --mock --dry-run
```

---

## ☁️ Despliegue en la Nube 24/7 (Render Free Tier)

El proyecto incluye un servidor de healthcheck HTTP interno en un hilo daemon (`bot.py`) y un archivo [`render.yaml`](file:///g:/Projects/autolinkedinpost/render.yaml) para ejecutarse **24/7 de forma 100% gratuita** en Render Web Services:

1. Haz un push de este repositorio a tu cuenta de GitHub (puede ser **privado**).
2. Entra a tu consola de [Render](https://dashboard.render.com/).
3. Haz clic en **New +** ➔ **Blueprint** (o **Web Service**) y vincula este repositorio.
4. En la sección de variables de entorno de Render, añade:
   - `LLM_PROVIDER`: `gemini` (o tu proveedor preferido)
   - `GEMINI_API_KEY` (o la key del proveedor configurado)
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `GH_USERNAME`
   - `GH_TOKEN` *(opcional para repositorios privados)*
   - `PYTHONIOENCODING`: `utf-8`
5. ¡Listo! El bot responderá al instante desde Telegram a cualquier hora sin necesidad de tener tu computadora encendida.

---

## 🍴 Zero-Config Fork & Run (Universal para Cualquier Usuario)

Este repositorio está arquitecturado para ser **100% amigable para forks sin valores hardcodeados**:

1. **Hacé clic en "Fork"** en GitHub para copiar este repositorio a tu cuenta.
2. En tu repositorio forkeado, andá a **Settings ➔ Secrets and variables ➔ Actions** y añadí:
   - `GEMINI_API_KEY` (o la API key de tu IA favorita: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `GROQ_API_KEY`)
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - *(Opcional)* `GH_TOKEN` (Personal Access Token para repositorios privados)
3. **Detección Automática de Usuario:** ¡No necesitás configurar `GH_USERNAME`! El workflow de GitHub Actions toma por defecto `github.repository_owner` (tu propio usuario de GitHub) e identifica tu autoría dinámicamente en los posts.

---

## ⏱️ Automatización Diaria con GitHub Actions

El workflow [`.github/workflows/daily_linkedin_post.yml`](file:///g:/Projects/autolinkedinpost/.github/workflows/daily_linkedin_post.yml) ejecuta el extractor todos los días a las **21:00 UTC** (18:00 ARG / 15:00 CDMX). Si no hubo actividad técnica relevante en las últimas 24 horas, el workflow finaliza en silencio sin generar spam.

Para personalizar la ejecución podés definir opcionalmente:
- `LLM_PROVIDER`: `gemini` | `openai` | `anthropic` | `deepseek` | `groq` | `openrouter`
- `LLM_MODEL`: Nombre del modelo (ej: `claude-3-7-sonnet-20250219`, `gpt-4o`)
- `GH_USERNAME`: Especificar un usuario distinto si deseás auditar otro perfil

---

---

## 🎨 Canva MCP Autónomo y Control de Calidad (QC) en 2 Capas

AutoLinkedInPost cuenta con integración autónoma con el protocolo **Canva MCP (Model Context Protocol)** para diseñar, auditar estéticamente y exportar carruseles PDF listos para subir a LinkedIn:

1. **Generación y Exportación Autónoma (src/canva_generator.py):**
   * Invoca Canva Magic Design vía MCP para crear presentaciones multipágina completas a partir de decisiones de arquitectura reales.
   * Guarda el diseño en tu cuenta de Canva y exporta el PDF de alta resolución de forma 100% desatendida.

2. **Control de Calidad (QC) en 2 Capas (src/pdf_evaluator.py):**
   * **Capa 1: Inspección Estructural (PyMuPDF - 0 Tokens, Fail-Fast):** Valida número de diapositivas (5-16 páginas), comprueba cero láminas vacías, filtra textos genéricos/placeholders (
eallygreatsite.com, lorem ipsum) y controla la densidad de palabras (<55 palabras/slide).
   * **Capa 2: Auditoría Visual Multimodal (Gemini Vision como Judge):** Renderiza en memoria todas las láminas a PNG y audita márgenes seguros (safe zones), centrado, contraste sobre fondo oscuro (#0F172A) y jerarquía tipográfica.

3. **Autenticación Open Source en 1 Comando (setup_canva.py):**
   * Ejecuta python setup_canva.py en local una sola vez.
   * Autentica vía loopback local RFC 8252 (http://127.0.0.1) sin requerir dominios públicos ni aprobaciones de waitlist de Canva.
   * Empaqueta tus credenciales en la variable CANVA_AUTH_TOKENS para correr en Render, Railway, Docker o GitHub Actions.

---

## 📂 Estructura del Código

```text
autolinkedinpost/
├── .github/workflows/
│   └── daily_linkedin_post.yml # Cron diario de GitHub Actions
├── src/
│   ├── canva_generator.py      # Cliente Canva MCP y exportador autónomo de PDF
│   ├── pdf_evaluator.py        # Control de Calidad en 2 capas (PyMuPDF + Gemini Vision)
│   ├── llm_client.py           # Cliente Multi-LLM universal (Gemini, Claude, OpenAI, DeepSeek, Groq, Ollama)
│   ├── evaluator.py            # LLM-as-a-Judge con rúbrica 1-5 y veracidad estricta
│   ├── github_extractor.py     # Extracción y filtrado inteligente de commits/eventos
│   ├── post_generator.py       # Motor de posts 2026, primera persona singular y prompts bilingües
│   ├── repo_analyzer.py        # Descarga y análisis profundo de README, árbol y stack
│   └── telegram_notifier.py    # Envío chunked seguro y bloques Tap-to-Copy para Telegram
├── bot.py                      # Bot interactivo con hilos concurrentes y healthcheck
├── main.py                     # CLI runner para cron o ejecución local con soporte Multi-LLM
├── setup_canva.py              # CLI para autenticación local en 1 comando y exportación de tokens
├── render.yaml                 # Blueprint para deploy automático en Render
├── requirements.txt            # Dependencias mínimas optimizadas
└── README.md                   # Documentación técnica completa
```

---

## 👨‍💻 Autoría y Licencia

Desarrollado con criterio de arquitectura senior, modularidad limpia y observabilidad.  
Distribuido bajo licencia **MIT**.

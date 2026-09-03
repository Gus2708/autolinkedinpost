# 🚀 AutoLinkedInPost — Senior Engineering Content Engine (Edición Multi-LLM 2026)

[🇺🇸 English Version](README.md) | [🇪🇸 Versión en Español](README.es.md)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Multi-LLM Ready](https://img.shields.io/badge/AI-Gemini%20%7C%20Claude%20%7C%20OpenAI%20%7C%20DeepSeek%20%7C%20Groq%20%7C%20Ollama-purple.svg)](https://github.com/Gus2708/autolinkedinpost)
[![Render Free 24/7](https://img.shields.io/badge/Deploy-Render%20Cloud-success.svg)](https://render.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**AutoLinkedInPost** es un sistema de ingeniería autónomo diseñado para desarrolladores senior, tech leads y fundadores técnicos que buscan posicionar su autoridad técnica frente a reclutadores internacionales y Engineering Managers en LinkedIn.

El sistema audita automáticamente tu actividad en GitHub, extrae decisiones de arquitectura reales y genera paquetes de publicación optimizados para el **Interest Graph de LinkedIn 2026** (Mobile-First, ganchos con corte de 220 caracteres, CTAs de debate técnico, carruseles nativos 4:5 Refero WebGL de 10 diapositivas y primer comentario limpio), todo validado mediante un **Quality Gate autónomo (LLM-as-a-Judge)** con política de **Cero Alucinación** y soporte universal para **múltiples proveedores de Inteligencia Artificial**.

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
               │     • Estructura Carrusel 10 Slides (4:5 - 1080x1350)  │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │         3. Humanizer Anti-AI-Slop & Quality Gates      │
               │     • Humanizer QC Gate: audita 24 patrones de IA      │
               │     • Veracidad absoluta y cero alucinaciones          │
               │     • Rúbrica LLM-as-a-Judge (Auto-Refinamiento)       │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │         4. Motor Nativo WebGL Paper Shaders a PDF      │
               │     • Gradientes mesh dinámicos (@paper-design/shaders)│
               │     • Aceleración SwiftShader en Playwright Chromium   │
               │     • PDF vectorial 1080x1350 px listo para publicar   │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │           5. Telegram Dispatcher & Interactive Bot     │
               │     • Bloques nativos monospaced "Tap-to-Copy" (<pre>) │
               │     • Entrega directa de PDF adjunto (sin prompt spam) │
               │     • Menú interactivo y switch bilingüe instantáneo   │
               └────────────────────────────────────────────────────────┘
```

---

## 🧠 Arquitectura Multi-LLM (Provider Pattern)

El motor de IA está completamente desacoplado mediante un adaptador agnóstico en [`src/llm_client.py`](src/llm_client.py), permitiéndote intercambiar proveedores y modelos simplemente cambiando variables de entorno:

| Proveedor | `LLM_PROVIDER` | Variable de API Key | Modelos Recomendados |
|---|---|---|---|
| **Google Gemini** | `gemini` | `GEMINI_API_KEY` | `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash` |
| **Anthropic Claude** | `anthropic` | `ANTHROPIC_API_KEY` | `claude-3-7-sonnet-20250219`, `claude-3-5-sonnet` |
| **OpenAI** | `openai` | `OPENAI_API_KEY` | `gpt-4o`, `gpt-4o-mini`, `o3-mini` |
| **DeepSeek** | `deepseek` | `DEEPSEEK_API_KEY` | `deepseek-chat`, `deepseek-reasoner` |
| **Groq** *(Inferencia ultra rápida)* | `groq` | `GROQ_API_KEY` | `llama-3.3-70b-versatile`, `mixtral-8x7b-32768` |
| **OpenRouter** *(Default)* | `openrouter` | `OPENROUTER_API_KEY` | `openai/gpt-4o-mini` *(default, con visión)*, `google/gemini-2.5-flash-lite` |
| **Ollama** *(Modelos Locales / Privados)* | `ollama` | `OLLAMA_BASE_URL` | `llama3.2`, `mistral`, `qwen2.5` |
| **Custom OpenAI-Compatible** | `custom` | `CUSTOM_LLM_API_KEY` | Endpoint en `CUSTOM_LLM_BASE_URL` (vLLM, LMStudio) |

> [!TIP]
> **Auto-Detección Heurística:** Si no defines `LLM_PROVIDER`, el sistema detecta automáticamente el proveedor según la API key que tengas configurada en tu entorno.

---

## ✨ Características Principales

### 🎯 1. Estrategia Algorítmica LinkedIn 2026
- **Ganchos de Alto Impacto (< 220 caracteres):** Tensión de ingeniería o contraste técnico en las primeras 2 líneas para forzar el clic en *"Ver más"*.
- **Mobile-First Real:** Párrafos de máximo 2 a 3 líneas con espacios en blanco obligatorios para lectura fluida en pantallas móviles.
- **CTAs de Debate Técnico:** Cada post cierra con una pregunta genuina de ingeniería sobre trade-offs reales. Las fórmulas mecánicas tipo *"guardá este post"* están prohibidas y las elimina el paso de humanización.
- **Regla del Primer Comentario (60 min):** Publicaciones 100% limpias de enlaces externos para evitar la penalización del 50% de alcance orgánico; el enlace al repositorio va formateado en el comentario semilla.

### 🛡️ 2. Quality Control (QC) de Humanizer Anti-AI-Slop y Copywriting de Conversión
- **Erradicación de los 24 Patrones de IA y Tells de Copywriting:** Pipeline de control de calidad dedicado (`src/humanizer_qc.py`) que audita el 100% de los textos generados (posts, comentarios y diapositivas de carrusel).
- **Eliminación de Clichés y Transiciones Artificiales:** Bloquea importancia inflada (*"un testimonio de"*, *"marca un hito"*, *"crucial"*), transiciones mecánicas (*"cabe destacar que"*, *"dicho esto"*, *"en su esencia"*), buzzwords vacíos (*"sin fisuras / seamless"*, *"game changer"*, *"intuitivo"*), estructuras binarias predecibles (*"No se trata de X, sino de Y"*) y tríadas de adjetivos.
- **Copywriting de Conversión Integrado:** Aplica *Clarity Over Cleverness* (test *"Now you can..."*), beneficios sobre características, especificidad radical, eliminación de calificadores débiles (*hedging*: *"casi"*, *"muy"*) y de signos de exclamación forzados.
- **CTAs de Alto Impacto:** Exige la fórmula `[Verbo de Acción] + [Qué se debate] + [Trade-off técnico]`, prohibiendo y erradicando CTAs pasivos o genéricos (*"hacé clic"*, *"aprendé más"*, *"guardá este post"*, *"seguime para más"*).
- **Voz en 1ª Persona Singular Obligatoria:** Garantiza autoría técnica personal (*"Decidí"*, *"Diseñé"*, *"Mi arquitectura"*), erradicando la voz pasiva y el camuflaje en plural (*"decidimos"*, *"nuestro equipo"*).
- **Score por Densidad:** Cada patrón distinto cuenta una sola vez y la penalización se normaliza por longitud, así un guion de carrusel largo no reprueba sólo por ser largo. La voz plural corporativa reprueba de forma directa, sin importar el puntaje.
- **Auto-Refinamiento Autónomo:** Si el post baja de 4.0/5.0, un LLM guiado por las directrices de Humanizer y Copywriting re-escribe los pasajes observados para recuperar ritmo, honestidad y naturalidad.
- **Juez que Falla Cerrado:** Si el evaluador no puede emitir veredicto (error de red, JSON inválido), el post se informa como *sin evaluar* en lugar de aprobarse en silencio. Los badges nunca muestran un puntaje que nadie calculó.

### 📑 3. Motor Nativo de Carruseles WebGL con Paper Shaders (1080x1350 px)
- **Formato Vertical 4:5 Nativo (1080 x 1350 px):** Ocupa 35% más de pantalla móvil en el feed de LinkedIn que formatos cuadrados o apaisados.
- **Seis Sistemas de Diseño de Ingeniería Rotativos:** Editorial Técnico, Terminal Brutalista, Swiss Grid, Blueprint Técnico, Monografía Académica y Linear Dark. Cada sistema define su propia tipografía, paleta OKLCH y composición de lámina. El sistema rota de forma determinista según la fecha y el repositorio sin estado en disco.
- **Composición Tipográfica Pura:** Tipografía cuidada y aire asimétrico sin cajas rígidas ni artefactos genéricos de IA.
- **Entrega Directa sin Fricción:** Un carrusel completo de 10 láminas se compila en un PDF vectorial nítido y se adjunta directamente a Telegram.

### 🌐 4. Generación Bilingüe Instantánea (ES / EN)
- Botón interactivo inline en Telegram (`🇬🇧 Generar todo en Inglés` / `🇪🇸 Generar en Español`) para traducir y adaptar el post completo, primer comentario y guion al estándar **US Tech Professional**.

### 📱 5. UX Móvil con Bloques "Tap-to-Copy"
- Toda la salida en Telegram se entrega en bloques de código monospaced `<pre>`. Con **un solo toque en la pantalla de tu celular**, copiás el texto limpio directamente al portapapeles sin arrastrar títulos, emojis ni metadatos.

### 🌐 6. Ecosistema de Skills Modulares y Motor de LinkedIn (`src/linkedin/`)
Integrado desde la suite modular de alto rendimiento para LinkedIn 2026, esta capa dota al sistema de habilidades especializadas, auditorías algorítmicas estrictas y publicación multi-backend:
- **11 Skills de Agente Modulares (`.agents/skills/`)**:
  - `linkedin-post-writer`: Redacción de publicaciones parametrizadas por objetivo y fórmulas de gancho.
  - `linkedin-hook-extractor`: Ingeniería inversa de fórmulas virales a partir de URLs de posts.
  - `linkedin-comment-drafter`: Redacción de comentarios de alto valor y reposts con comentarios.
  - `linkedin-reply-handler`: Manejo contextual de respuestas a comentarios respetando el límite de 2 niveles.
  - `linkedin-thread-monitor`: Monitoreo de respuestas del autor en la ventana dorada de 6 a 24 horas.
  - `linkedin-profile-optimizer`: Auditoría y optimización integral de titular, Acerca de, Destacados y Experiencia.
  - `linkedin-content-planner`: Planes semanales temáticos de contenido y distribución de pilares.
  - `linkedin-employee-advocacy`: Programa de embajadores de equipo y métricas de cadencia.
  - `linkedin-engager-analytics`: Segmentación ICP de interacciones (pares, prospectos, aspiracionales).
  - `linkedin-repurposer`: Adaptación de notas, transcripciones o artículos a múltiples ángulos de post.
  - `linkedin-humanizer`: Detección y eliminación de rastros sintéticos de IA en borradores.
- **8 Guías de Referencia en Profundidad (`docs/references/`)**:
  - `hook-formulas.md`: 20 fórmulas canónicas de gancho (F1–F20) en formato largo, corto y estructural.
  - `founder-topics.md`: 10 ángulos de fundador (A1–A10) que capitalizan tensión técnica y de producto.
  - `algorithm-heuristics.md`: Mecánicas de dwell time, penalizaciones por enlaces y velocidad de comentarios.
  - Taxonomía de métricas, benchmarks de industria, perfiles de voz y validación de contenido no confiable.
- **Motor de Integración (`src/linkedin/`)**:
  - `url_parser.py`: Extracción robusta de URNs y IDs numéricos para posts, shares y comentarios.
  - `approval.py`: Máquina de estados `ApprovalGate` que garantiza confirmación humana explícita antes de publicar.
  - `hooks.py`: Acceso tipado a las 20 fórmulas de gancho y 10 ángulos de fundador.
  - `backends.py`: Selector de backends con soporte para Publora REST API, Pixfaro API y fallback Tier 0 (Modo Borrador sin credenciales).
- **Quality Gates Algorítmicos 2026**:
  - `audit_emoji_density`: Límite estricto de máximo 3 emojis para mantener credibilidad técnica senior.
  - `audit_algorithm_heuristics`: Detección de penalizaciones por enlaces externos tempranos (líneas 1–3) y bloques monolíticos (> 5 líneas sin espacio en blanco).


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
# Proveedor de IA (Por defecto: OpenRouter con Claude Sonnet 4.5)
LLM_PROVIDER=openrouter
LLM_MODEL=anthropic/claude-sonnet-4.5
OPENROUTER_API_KEY="sk-or-v1-..."

# Proveedores directos alternativos (fallback opcional)
# GEMINI_API_KEY="tu_gemini_api_key"
# ANTHROPIC_API_KEY="sk-ant-..."
# OPENAI_API_KEY="sk-..."

# Telegram Bot
TELEGRAM_BOT_TOKEN="tu_token_de_botfather"
TELEGRAM_CHAT_ID="tu_id_de_telegram"

# GitHub
GH_USERNAME="tu_usuario_github"
GH_TOKEN=""  # Opcional (PAT de GitHub si deseas analizar repositorios privados)
LOOKBACK_DAYS=1
PYTHONIOENCODING=utf-8

# Publicación Automática en LinkedIn 2026 (Opcional — Tier 1)
# Plan gratuito (15 posts/mes): https://app.publora.com/signup
PUBLORA_API_KEY="sk_tu_api_key_publora"
LINKEDIN_PLATFORM_ID="linkedin-tu_channel_id"

# Analítica de Interacciones y Monitoreo de Hilos (Opcional para skills)
# Crédito gratuito de $5/mes: https://console.apify.com/sign-up
APIFY_TOKEN="apify_api_tu_token"
PIXFARO_TOKEN="pf_live_tu_token"
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
   - 📑 **Carrusel Nativo 4:5 PDF (Refero / WebGL) de 10 Slides**.
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

El proyecto incluye un servidor de healthcheck HTTP interno en un hilo daemon (`bot.py`) y un archivo [`render.yaml`](render.yaml) para ejecutarse **24/7 en el plan gratuito** de Render Web Services:

### 1. Crear el Web Service en Render

1. Entrá a tu consola de [Render](https://dashboard.render.com/).
2. Hacé clic en **New +** ➔ **Web Service** (o **Blueprint** usando [`render.yaml`](render.yaml)) y vinculá este repositorio.
3. Configurá los comandos de ejecución:
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt && playwright install chromium
     ```
     > [!IMPORTANT]
     > **No agregues `--with-deps`**: el instalador de Playwright con `--with-deps` intenta ejecutar `sudo apt-get`. Como Render compila como usuario sin permisos de root, fallará con `su: Authentication failure`. La descarga sin `--with-deps` instala el binario de Chromium directamente en tu espacio de usuario.
   - **Start Command**:
     ```bash
     python bot.py
     ```

### 2. Variables de Entorno (Environment Variables)

En la pestaña **Environment** de tu servicio en Render, configurá las siguientes variables:

| Variable | Valor / Ejemplo | Descripción |
|---|---|---|
| `LLM_PROVIDER` | `openrouter` (o `gemini`, `openai`, `anthropic`) | Proveedor de LLM activo. |
| `LLM_MODEL` | `anthropic/claude-sonnet-4.5` (o `openai/gpt-4o-mini`) | Modelo específico a utilizar. |
| `OPENROUTER_API_KEY` | `sk-or-v1-...` | API Key de OpenRouter *(revisá que no tenga typos)*. |
| `GEMINI_API_KEY` | *(Opcional)* `AIzaSy...` | API Key de Google Gemini (si usás Gemini como proveedor o fallback). |
| `TELEGRAM_BOT_TOKEN` | `866038...:AAEY...` | Token del bot provisto por `@BotFather`. |
| `TELEGRAM_CHAT_ID` | `852084...` | Tu ID de Telegram para restringir el bot solo a tu cuenta. |
| `GH_USERNAME` | `tu_usuario` | Tu nombre de usuario de GitHub para listar y analizar repositorios. |
| `GH_TOKEN` | `ghp_...` | **Personal Access Token (Classic)** con scope `repo`. |
| `PYTHONIOENCODING` | `utf-8` | Garantiza encoding UTF-8 en logs y outputs. |
| `PYTHONUNBUFFERED` | `1` | Fuerza a Python a enviar logs inmediatamente a la consola de Render. |

> [!WARNING]
> **Por qué `GH_TOKEN` es indispensable en Render:**
> Sin token, GitHub limita las consultas anónimas a **60 peticiones por hora por IP**. En Render Free Tier, tu contenedor comparte la IP pública de salida con cientos de otras aplicaciones: la cuota anónima suele estar agotada y GitHub responde con `403 Rate limit exceeded` (lo que hace que `/menu` devuelva error).
> Configurar un PAT clásico con permiso `repo` te asigna **5.000 peticiones por hora dedicadas exclusivamente a tu cuenta**.

### 3. Evitar que Render se duerma (Pinger cada 10 min)

El Free Tier de Render **apaga/suspende los Web Services tras 15 minutos sin tráfico HTTP entrante**. Como el bot usa long-polling (`getUpdates` saliente hacia Telegram), Render no detecta peticiones entrantes y suspende el bot, dejando de responder comandos como `/menu`.

Para mantenerlo activo 24/7 sin costo:
1. Creá una cuenta gratuita en [cron-job.org](https://cron-job.org) o [UptimeRobot](https://uptimerobot.com).
2. Configurá un job que realice una petición HTTP **`GET` cada 10 minutos** a la URL pública de tu servicio:
   ```text
   https://tu-servicio.onrender.com
   ```
3. El servidor interno de `bot.py` responderá con `200 OK`, manteniendo el proceso siempre despierto y listo para atender Telegram al instante.

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

El workflow [`.github/workflows/daily_linkedin_post.yml`](.github/workflows/daily_linkedin_post.yml) ejecuta el extractor todos los días a las **21:20 UTC** (18:20 ARG / 15:20 CDMX), desfasado del minuto 0 para esquivar la congestión de GitHub. Si no hubo actividad técnica relevante en las últimas 24 horas, el workflow finaliza en silencio sin generar spam.

> [!WARNING]
> El evento `schedule` de GitHub es best-effort y **descarta ejecuciones bajo carga**:
> medido acá, sólo 3 de 5 disparos diarios ocurrieron entre el 24 y el 28 de agosto de 2026.
> Para una entrega confiable, disparalo desde un scheduler externo como se explica en
> [`docs/scheduling.md`](docs/scheduling.md). El cron queda como respaldo y un guard evita
> la doble publicación.

Para personalizar la ejecución podés definir opcionalmente:
- `LLM_PROVIDER`: `gemini` | `openai` | `anthropic` | `deepseek` | `groq` | `openrouter`
- `LLM_MODEL`: Nombre del modelo (ej: `claude-3-7-sonnet-20250219`, `gpt-4o`)
- `GH_USERNAME`: Especificar un usuario distinto si deseás auditar otro perfil
- `GH_AUTHOR_EMAILS`: Emails con los que commiteás, separados por coma. GitHub sólo vincula un commit a tu cuenta cuando el email del autor está verificado en tu perfil: los commits hechos desde una máquina con otra dirección no se reconocen como propios y quedan filtrados.

Consultá [`.env.example`](.env.example) para la lista completa de variables soportadas, incluidos los ajustes opcionales (`LLM_MAX_OUTPUT_TOKENS`, `LLM_TIMEOUT_SECONDS`, `LUCIDE_VERSION`, `PAPER_SHADERS_VERSION`).

---

## 🧪 Tests

La batería cubre los parsers, los gates de calidad y la lógica de entrega. No toca la red ni Chromium, así que corre en unos dos segundos.

```bash
pip install -r requirements-dev.txt
python -m pytest
```

[`.github/workflows/tests.yml`](.github/workflows/tests.yml) la ejecuta en cada push y en cada pull request.

---

## 🎨 Carruseles Nativos WebGL con Paper Shaders y Control de Calidad (QC)

AutoLinkedInPost compila carruseles en PDF vertical 4:5 directamente en el servidor/máquina local utilizando **Playwright Chromium**, **aceleración SwiftShader** y **Paper Shaders WebGL** (`@paper-design/shaders`):

1. **Pipeline Nativo HTML/CSS y WebGL (`src/carousel_renderer.py`):**
   * **Renderizado WebGL sin GPU dedicada:** Ejecuta Chromium headless con SwiftShader (`--use-gl=angle --use-angle=swiftshader --enable-webgl`) para crear fondos de gradientes orgánicos con textura analógica de grano (`u_grainOverlay: 0.05`).
   * **Rotación Determinista de Temas (`src/theme_manager.py`):** Un único tema Refero coherente por publicación, derivado de la fecha UTC y el nombre del repositorio. Sin contador compartido en disco, así que un checkout limpio de CI también rota.
   * **Dependencias de CDN Fijadas:** Lucide y Paper Shaders se cargan en versiones exactas. Con `@latest`, un release del paquete podía cambiar el resultado de una corrida desatendida.
   * **Esperas Deterministas:** El exportador espera señales explícitas de la página (iconos inicializados, `document.fonts.ready` resuelto, shaders montados) en lugar de un sleep fijo, así un CDN lento degrada de forma ruidosa en vez de producir un PDF a medio renderizar.
   * **Cero Errores de Renderizado en Móviles:** Sin `box-shadow` borroso ni transparencias problemáticas, evitando cajas negras opacas en iOS PDFKit, Android y Telegram.

2. **Control de Calidad en Dos Capas (`src/pdf_evaluator.py`):**
   * **Capa 1 — Estructural (0 tokens):** PyMuPDF verifica cantidad de páginas, relación 4:5, láminas vacías, placeholders prohibidos, colisiones con las safe-zones y coherencia cromática del fondo. Es la capa que guía el bucle de auto-reparación ajustando escala y tema.
   * **Capa 2 — Visual (multimodal):** Corre **una sola vez**, sobre el mejor candidato estructural, en vez de una vez por intento. El bucle además corta cuando no hay acción de reparación aplicable, porque los defectos que vienen del guion no se arreglan re-renderizando.
   * **Reporte Honesto:** Si la auditoría visual no puede correr (falta `GEMINI_API_KEY`), el resultado se informa como *sólo estructural* en lugar de devolver una aprobación que nadie verificó.

3. **Motor Humanizer Anti-AI-Slop (`src/humanizer_qc.py`):**
   * **24 Patrones de IA Auditados:** Audita cada texto (posts, comentarios y guion de carrusel) erradicando clichés corporativos, buzzwords de marketing y fórmulas binarias predecibles.
   * **Sanitización por Idioma:** Español e inglés mantienen tablas de reemplazo separadas, así un post en inglés nunca recibe sustituciones en castellano.
   * **Experiencia Telegram Limpia:** Adjunta directamente el documento PDF listo para publicar, eliminando bloques de texto redundantes o prompts verbosos.

---

## 📂 Estructura del Código

```text
autolinkedinpost/
├── .github/workflows/
│   ├── daily_linkedin_post.yml # Cron diario de GitHub Actions
│   └── tests.yml               # Batería de tests en cada push y pull request
├── .agents/skills/
│   ├── humanizer-zh/           # Reglas y vocabulario del skill Humanizer anti-slop
│   └── copywriting/            # Frameworks de conversión, ganchos de titulares y CTAs de acción
├── src/
│   ├── carousel_renderer.py    # Renderizador nativo 4:5 HTML/CSS y Paper Shaders WebGL a PDF
│   ├── theme_manager.py        # Temas de diseño Refero con rotación determinista por fecha
│   ├── pdf_evaluator.py        # QC del carrusel en dos capas (estructural PyMuPDF + visual multimodal)
│   ├── humanizer_qc.py         # Control de Calidad (QC) Humanizer anti-slop y auto-refinamiento
│   ├── llm_client.py           # Cliente Multi-LLM universal (Gemini, Claude, OpenAI, DeepSeek, Groq, Ollama)
│   ├── evaluator.py            # LLM-as-a-Judge con rúbrica 1-5 y veracidad estricta
│   ├── github_extractor.py     # Extracción de commits/eventos con filtrado por autoría real
│   ├── post_generator.py       # Motor de posts 2026, primera persona singular y prompts bilingües
│   ├── repo_analyzer.py        # Descarga y análisis profundo de README, árbol y stack
│   └── telegram_notifier.py    # Envío HTML limpio con bloques Tap-to-Copy y PDF adjunto directo
├── tests/                      # Batería de tests (parsers, gates de calidad, entrega)
├── bot.py                      # Bot interactivo con hilos concurrentes y healthcheck
├── main.py                     # CLI runner para cron o ejecución local con soporte Multi-LLM
├── render.yaml                 # Blueprint para deploy automático en Render
├── requirements.txt            # Dependencias de producción, acotadas por major
├── requirements-dev.txt        # Dependencias de desarrollo y CI
├── pytest.ini                  # Configuración del runner de tests
├── README.md                   # Documentación técnica en inglés
└── README.es.md                # Documentación técnica en español
```

---

## 👨‍💻 Autoría y Licencia

Desarrollado con criterio de arquitectura senior, modularidad limpia y observabilidad.  
Distribuido bajo licencia **MIT**.

# 🚀 AutoLinkedInPost — Senior Engineering Content Engine (Multi-LLM 2026 Edition)

[🇺🇸 English Version](README.md) | [🇪🇸 Versión en Español](README.es.md)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/Gus2708/autolinkedinpost/actions/workflows/ci.yml/badge.svg)](https://github.com/Gus2708/autolinkedinpost/actions/workflows/ci.yml)
[![Multi-LLM Ready](https://img.shields.io/badge/AI-Gemini%20%7C%20Claude%20%7C%20OpenAI%20%7C%20DeepSeek%20%7C%20Groq%20%7C%20Ollama-purple.svg)](https://github.com/Gus2708/autolinkedinpost)
[![Render Free 24/7](https://img.shields.io/badge/Deploy-Render%20Cloud-success.svg)](https://render.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**AutoLinkedInPost** is an autonomous engineering content automation engine built for senior software engineers, tech leads, and technical founders looking to establish technical authority with international recruiters and Engineering Managers on LinkedIn.

The engine continuously audits your real GitHub activity, extracts architectural design decisions, and produces complete publication packages optimized for the **LinkedIn 2026 Interest Graph** (Mobile-First 2-line paragraphs, 220-character hook cuts, debate-driven CTAs, 10-slide native 4:5 Refero WebGL carousels, and clean first comments). All generated content is enforced through an automated **LLM-as-a-Judge Quality Gate** under a strict **Zero-Hallucination Grounding Policy** and powered by a universal **Multi-LLM Provider Architecture**.

---

## 🏛️ System Architecture

```text
               ┌────────────────────────────────────────────────────────┐
               │              GitHub Repository / Activity              │
               │   (Commits, PRs, Tree Structure, README, Tech Stack)   │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │           1. GitHub Extractor & Deep Analyzer          │
               │     • Filters trivial noise (docs, typo fixes, merges) │
               │     • Extracts architecture context & key files        │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │         2. Multi-LLM Engine (Provider Pattern)         │
               │     • Gemini 3.7 / Claude 3.7 / GPT-4o / DeepSeek /    │
               │       Groq / OpenRouter / Ollama (Local Models)        │
               │     • 1st-Person Singular Voice ("I designed/built")   │
               │     • Mobile-First Format (2-line paragraphs)          │
               │     • 10-Slide Carousel Structure (4:5 - 1080x1350)    │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │         3. Humanizer Anti-AI-Slop & Quality Gates      │
               │     • Humanizer QC Gate: scans 24 AI slop patterns     │
               │     • Zero-Hallucination & Factual Grounding Check     │
               │     • LLM-as-a-Judge Rubric (Auto-Refinement Loop)     │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │         4. Native Paper Shaders WebGL PDF Renderer     │
               │     • Dynamic WebGL Mesh Gradients (@paper-design)     │
               │     • SwiftShader GPU acceleration in Playwright       │
               │     • Crisp Vector 1080x1350 px PDF ready to publish   │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │           5. Telegram Dispatcher & Interactive Bot     │
               │     • Native "Tap-to-Copy" Code Blocks (<pre>)         │
               │     • Direct Carousel PDF Delivery (No prompt walls)   │
               │     • Interactive Repository Menu & Instant Bilingual  │
               └────────────────────────────────────────────────────────┘
```

---

## 🧠 Multi-LLM Provider Architecture

The AI layer is completely decoupled using an agnostic Provider Pattern in [`src/llm_client.py`](src/llm_client.py), allowing seamless model switching via standard environment variables:

| Provider | `LLM_PROVIDER` | API Key Variable | Recommended Models |
|---|---|---|---|
| **Google Gemini** | `gemini` | `GEMINI_API_KEY` | `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash` |
| **Anthropic Claude** | `anthropic` | `ANTHROPIC_API_KEY` | `claude-3-7-sonnet-20250219`, `claude-3-5-sonnet` |
| **OpenAI** | `openai` | `OPENAI_API_KEY` | `gpt-4o`, `gpt-4o-mini`, `o3-mini` |
| **DeepSeek** | `deepseek` | `DEEPSEEK_API_KEY` | `deepseek-chat`, `deepseek-reasoner` |
| **Groq** *(Ultra-fast inference)* | `groq` | `GROQ_API_KEY` | `llama-3.3-70b-versatile`, `mixtral-8x7b-32768` |
| **OpenRouter** *(Default)* | `openrouter` | `OPENROUTER_API_KEY` | `openai/gpt-4o-mini` *(default, con visión)*, `google/gemini-2.5-flash-lite` |
| **Ollama** *(Local / Self-Hosted)* | `ollama` | `OLLAMA_BASE_URL` | `llama3.2`, `mistral`, `qwen2.5` |
| **Custom OpenAI-Compatible** | `custom` | `CUSTOM_LLM_API_KEY` | Endpoint at `CUSTOM_LLM_BASE_URL` (vLLM, LMStudio) |

> [!TIP]
> **Heuristic Auto-Detection:** If `LLM_PROVIDER` is omitted, the system automatically detects the provider based on the configured API key in your environment.

---

## ✨ Core Engineering Features

### 🎯 1. LinkedIn 2026 Algorithmic Optimization
- **High-Impact Hooks (< 220 characters):** Real technical tension or architectural trade-offs placed before the "See more" fold.
- **True Mobile-First Formatting:** Short 2 to 3-line paragraphs with mandatory whitespace for clean skimming on mobile screens.
- **Debate-Driven CTAs:** Every post closes with a genuine engineering question about real trade-offs. Boilerplate prompts like *"save this post"* are explicitly banned and stripped by the Humanizer pass.
- **First Comment Rule (60-minute window):** 100% clean post bodies without outbound links to avoid the 50% algorithmic link penalty; clean repo links are delivered in the seed comment.

### 🛡️ 2. Humanizer Anti-AI-Slop & Conversion Copywriting Quality Control (QC)
- **Eradication of AI Slop & Copywriting Tells:** Dedicated QC pipeline (`src/humanizer_qc.py`) auditing 100% of bot texts (posts, comments, carousels) against WikiProject AI Cleanup, Humanizer, and conversion copywriting standards.
- **Banned Artificial Tells & Transitions:** Eliminates inflated significance (*"a testament to"*, *"pivotal moment"*, *"crucial"*), mechanical transitions (*"that being said"*, *"it's worth noting that"*, *"at its core"*), marketing buzzwords (*"seamless"*, *"game-changer"*, *"intuitive"*), formulaic binary contrasts (*"it's not about X, it's about Y"*), and rule-of-three adjective clichés.
- **Integrated Conversion Copywriting:** Enforces *Clarity Over Cleverness* (the *"Now you can..."* gut check), benefits over features, radical specificity, removal of hedging qualifiers (*confident over qualified*: no *"almost"*, *"very"*), and zero exclamation marks.
- **High-Converting Action CTAs:** Mandates the formula `[Action Verb] + [What to explore/discuss] + [Technical trade-off question]`. Strictly bans and eliminates weak or passive CTAs (*"click here"*, *"learn more"*, *"save this post"*, *"follow for more"*).
- **Enforced 1st-Person Singular Voice:** Mandates genuine personal engineering ownership (*"I decided"*, *"I built"*, *"My architecture"*), eliminating passive voice and corporate plural camouflage (*"we designed"*, *"our team"*).
- **Density-Based Scoring:** Violations are counted once per distinct pattern and normalized by text length, so a long carousel script is not penalized simply for being long. Corporate plural voice fails the gate outright, regardless of score.
- **Automated Self-Refinement:** If the post scores below 4.0/5.0, an automated LLM pass rewrites the offending passages using Humanizer and Copywriting directives to restore rhythm, clarity, and authority.
- **Fail-Closed Judging:** If the LLM judge cannot produce a verdict (network error, malformed JSON), the post is reported as *unevaluated* rather than silently approved. Quality badges never show a score nobody computed.

### 📑 3. Native 4:5 Paper Shaders WebGL Carousel Engine (1080x1350 px)
- **True 4:5 Vertical Portrait (1080 x 1350 px):** Covers 35% more vertical viewport space on mobile LinkedIn feeds than square or horizontal formats.
- **Six Rotating Engineering Design Systems:** Editorial Técnico, Terminal Brutalista, Swiss Grid, Blueprint Técnico, Monografía Académica, and Linear Dark. Each system defines its own typography, OKLCH palette, and slide composition. The system rotates deterministically by date and repository seed without on-disk state.
- **Pure Typographic Layouts:** Clean typography and asymmetric breathing room without boxy containers or generic AI mesh artifacts.
- **Direct Attachment Delivery:** A full 10-slide carousel renders in crisp vector PDF and is attached directly to Telegram.

### 🌐 4. Instant Bilingual Generation (English / Spanish)
- Interactive inline Telegram button (`🇬🇧 Generate in English` / `🇪🇸 Generate in Spanish`) allowing on-the-fly regeneration adapted to **US Tech Industry Standards** or native Spanish.

### 📱 5. Mobile UX with Native "Tap-to-Copy" Blocks
- All output in Telegram is delivered in isolated `<pre>` code blocks. A **single tap on iOS or Android** copies the exact clean block to your clipboard without dragging headers, emojis, or labels.

### 🌐 6. LinkedIn Optimization Ecosystem & Modular Skills (`src/linkedin/`)
Integrated from the specialized LinkedIn 2026 suite, this modular architecture equips the project with 11 agent skills, 8 reference manuals, and a dedicated integration engine:
- **11 Modular Agent Skills (`.agents/skills/`)**:
  - `linkedin-post-writer`: Drafts high-performing posts parameterized by engagement goals and hook formulas.
  - `linkedin-hook-extractor`: Reverse-engineers canonical hook structures from viral LinkedIn URLs.
  - `linkedin-comment-drafter`: Generates insightful top-level comments and reshares with commentary.
  - `linkedin-reply-handler`: Drafts contextual replies to specific comments respecting 2-level thread flattening.
  - `linkedin-thread-monitor`: Tracks author replies during the critical 6-24h warm engagement window.
  - `linkedin-profile-optimizer`: End-to-end audit and conversion rewrite for Headline, About, Featured, and Experience.
  - `linkedin-content-planner`: 7-day thematic content calendar with daily hooks, CTAs, and engagement targets.
  - `linkedin-employee-advocacy`: Coordinates engineering/sales advocacy programs with cadence benchmarks.
  - `linkedin-engager-analytics`: Segments post engagers by ICP fit (peer, prospect, aspirational).
  - `linkedin-repurposer`: Transforms long-form technical notes into multiple targeted LinkedIn posts.
  - `linkedin-humanizer`: Audits and strips AI tells, formulaic binaries, and robotic cadence from drafts.
- **8 Deep Reference Guides (`docs/references/`)**:
  - `hook-formulas.md`: 20 canonical hook formulas (F1–F20) across long-form, short-form, and structural designs.
  - `founder-topics.md`: 10 founder content angles (A1–A10) mining technical conviction and startup tension.
  - `algorithm-heuristics.md`: Dwell-time mechanics, link penalties, and golden hour velocity rules.
  - Plus industry benchmarks, engagement metrics taxonomy, voice profiles, and untrusted content safeguards.
- **Platform Integration Engine (`src/linkedin/`)**:
  - `url_parser.py`: Robust parsing and canonical URN resolution for posts, activities, shares, and comments.
  - `approval.py`: `ApprovalGate` state machine enforcing explicit human signoff before any network mutation.
  - `hooks.py`: Strongly-typed registry for formulas F1-F20 and founder angles A1-A10.
  - `backends.py`: Multi-backend selector supporting Publora REST API, Pixfaro API, and automatic zero-credential Tier 0 (Draft mode) fallback.
- **2026 Algorithmic Quality Gates**:
  - `audit_emoji_density`: Enforces a strict ceiling of maximum 3 emojis per post to preserve senior technical credibility.
  - `audit_algorithm_heuristics`: Identifies early external link penalties (lines 1–3) and monolithic text walls (> 5 lines without whitespace).


---

## 🚀 Quickstart & Installation

### 1. Clone repository & initialize virtual environment
```bash
git clone https://github.com/Gus2708/autolinkedinpost.git
cd autolinkedinpost
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate
```

### 2. Install dependencies & browser engine
```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure environment variables
Copy the template:
```bash
cp .env.example .env
```
Fill in your credentials:
```env
# AI Provider Configuration (Default: OpenRouter with Claude Sonnet 4.5)
LLM_PROVIDER=openrouter
LLM_MODEL=anthropic/claude-sonnet-4.5
OPENROUTER_API_KEY="sk-or-v1-..."

# Alternative direct provider keys (optional fallback)
# GEMINI_API_KEY="your_gemini_api_key"
# ANTHROPIC_API_KEY="sk-ant-..."
# OPENAI_API_KEY="sk-..."

# Telegram Bot
TELEGRAM_BOT_TOKEN="your_botfather_token"
TELEGRAM_CHAT_ID="your_telegram_numeric_id"

# GitHub
GH_USERNAME="your_github_username"
GH_TOKEN=""  # Optional GitHub PAT (required for private repositories)
LOOKBACK_DAYS=1
PYTHONIOENCODING=utf-8

# LinkedIn 2026 Automated Publishing (Optional — Tier 1)
# Sign up free (15 posts/month): https://app.publora.com/signup
PUBLORA_API_KEY="sk_your_publora_key"
LINKEDIN_PLATFORM_ID="linkedin-your_connection_id"

# LinkedIn Analytics & Thread Monitoring (Optional for agent skills)
# Free $5/month credit: https://console.apify.com/sign-up
APIFY_TOKEN="apify_api_your_token"
PIXFARO_TOKEN="pf_live_your_token"
```

---

## 🛠️ Usage Modes

### Mode 1: Interactive Telegram Bot (Recommended)
Run the bot to explore your repositories and generate engineering showcases on demand directly from your phone:
```bash
python bot.py
```
1. Open your Telegram bot and send `/menu` or `/proyectos`.
2. Tap any repository from the interactive paginated list.
3. Instantly receive:
   - 📝 **LinkedIn Post** (Tap-to-copy).
   - 💬 **First Comment** (With clean GitHub link).
   - 📸 **Visual Suggestion** (C4 architecture diagram / terminal benchmark).
   - 📑 **10-Slide Native 4:5 PDF Carousel (Refero / WebGL)**.
   - 🇬🇧 **Bilingual toggle button**.

### Mode 2: Daily Activity CLI
Scans commit activity over the past 24 hours and dispatches formatted drafts to Telegram:
```bash
# Run daily review with default LLM
python main.py

# Run with specific LLM provider and model
python main.py --provider openai --model gpt-4o
python main.py --provider anthropic --model claude-3-7-sonnet-20250219
python main.py --provider deepseek --model deepseek-chat

# Generate directly in English
python main.py --lang en

# Scan activity for the last 7 days
python main.py --days 7

# Local mock dry-run (no Telegram message sent)
python main.py --mock --dry-run
```

---

## ☁️ 24/7 Cloud Deployment (Render Free Tier)

The project includes an embedded HTTP healthcheck daemon (`bot.py`) and a [`render.yaml`](render.yaml) blueprint to run **24/7 on the free tier** of Render Web Services:

### 1. Create the Web Service in Render

1. Open your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** ➔ **Web Service** (or **Blueprint** using [`render.yaml`](render.yaml)) and connect this repo.
3. Configure the execution settings:
   - **Runtime**: `Python 3`
   - **Build Command**:
     ```bash
     pip install -r requirements.txt && playwright install chromium
     ```
     > [!IMPORTANT]
     > **Do not add `--with-deps`**: running Playwright with `--with-deps` attempts to run `sudo apt-get`. Since Render builds run without root privileges, it will fail with `su: Authentication failure`. Installing without `--with-deps` downloads the Chromium browser binary directly into user space.
   - **Start Command**:
     ```bash
     python bot.py
     ```

### 2. Environment Variables

In the **Environment** tab of your Render service, configure:

| Variable | Value / Example | Description |
|---|---|---|
| `LLM_PROVIDER` | `openrouter` (or `gemini`, `openai`, `anthropic`) | Active LLM provider. |
| `LLM_MODEL` | `anthropic/claude-sonnet-4.5` (or `openai/gpt-4o-mini`) | Target model identifier. |
| `OPENROUTER_API_KEY` | `sk-or-v1-...` | OpenRouter API Key *(ensure no typos)*. |
| `GEMINI_API_KEY` | *(Optional)* `AIzaSy...` | Google Gemini API Key (if used as provider or fallback). |
| `TELEGRAM_BOT_TOKEN` | `866038...:AAEY...` | Telegram bot token from `@BotFather`. |
| `TELEGRAM_CHAT_ID` | `852084...` | Your Telegram chat ID to whitelist commands. |
| `GH_USERNAME` | `your_username` | GitHub handle to fetch and analyze repositories. |
| `GH_TOKEN` | `ghp_...` | **Personal Access Token (Classic)** with `repo` scope. |
| `PUBLORA_API_KEY` | *(Optional)* `sk_...` | Publora API key for direct LinkedIn and carousel draft publishing. |
| `LINKEDIN_PLATFORM_ID` | *(Optional)* `linkedin-...` | Publora LinkedIn connection ID. |
| `PYTHONIOENCODING` | `utf-8` | Ensures UTF-8 encoding across logs and system stdout. |
| `PYTHONUNBUFFERED` | `1` | Forces immediate log flushing to Render console. |

> [!WARNING]
> **Why `GH_TOKEN` is mandatory on Render:**
> Unauthenticated requests to GitHub are capped at **60 requests/hour per IP**. On Render Free Tier, your container shares an outbound IP with hundreds of other apps, meaning the anonymous quota is frequently exhausted (`403 Rate limit exceeded`), breaking `/menu`.
> A Classic PAT with `repo` scope gives your account **5,000 requests/hour dedicated exclusively to your user**.

### 3. Prevent Inactivity Suspension (10-min Pinger)

Render Free Tier **spins down Web Services after 15 minutes of inbound HTTP inactivity**. Because the bot uses long-polling (`getUpdates` outgoing to Telegram), Render sees no inbound traffic and suspends the instance.

To keep it awake 24/7 for free:
1. Create a free account on [cron-job.org](https://cron-job.org) or [UptimeRobot](https://uptimerobot.com).
2. Set up a job performing an HTTP **`GET` every 10 minutes** to your public Render service URL:
   ```text
   https://your-service.onrender.com
   ```
3. The internal healthcheck server in `bot.py` will return `200 OK`, ensuring the instance remains active and ready to handle Telegram commands instantly.

---

## 🍴 Zero-Config Fork & Run (100% Universal)

This repository is architected to be **completely fork-friendly with zero hardcoded defaults**:

1. **Click "Fork"** on GitHub to copy this repository to your account.
2. In your forked repository, go to **Settings ➔ Secrets and variables ➔ Actions** and add:
   - `GEMINI_API_KEY` (or your preferred LLM API key, e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`, `GROQ_API_KEY`)
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - *(Optional)* `GH_TOKEN` (Personal Access Token for private repositories)
   - *(Optional for automated carousel publishing)* `PUBLORA_API_KEY` and `LINKEDIN_PLATFORM_ID`
3. **Automatic Owner Detection:** You do **not** even need to specify `GH_USERNAME`! The GitHub Actions workflow automatically falls back to `github.repository_owner` (your GitHub handle) and dynamically attributes your identity in the generated showcases.

---

## ⏱️ Daily GitHub Actions Automation

The workflow [`.github/workflows/daily_linkedin_post.yml`](.github/workflows/daily_linkedin_post.yml) runs daily at **21:20 UTC** (18:20 ARG / 15:20 CDMX), offset from the top of the hour to avoid GitHub's scheduling congestion. If no relevant commit activity occurred in the last 24 hours, the workflow exits silently without spamming.

> [!WARNING]
> GitHub's `schedule` event is best-effort and **drops runs under load** — measured here,
> only 3 of 5 expected daily triggers fired between Aug 24 and Aug 28, 2026. For reliable
> delivery, drive the workflow from an external scheduler as described in
> [`docs/scheduling.md`](docs/scheduling.md). The cron stays as a fallback and a duplicate
> guard prevents double posting.

To customize your automated run, you can optionally define:
- `LLM_PROVIDER`: `gemini` | `openai` | `anthropic` | `deepseek` | `groq` | `openrouter`
- `LLM_MODEL`: Specific model name (e.g. `claude-3-7-sonnet-20250219`, `gpt-4o`)
- `GH_USERNAME`: Override username if auditing a different profile
- `GH_AUTHOR_EMAILS`: Comma-separated emails you commit with. GitHub only links a commit to your account when the author email is verified on your profile — commits made from a machine using a different address are otherwise not recognized as yours and get filtered out.

See [`.env.example`](.env.example) for the full list of supported variables, including optional tuning knobs (`LLM_MAX_OUTPUT_TOKENS`, `LLM_TIMEOUT_SECONDS`, `LUCIDE_VERSION`, `PAPER_SHADERS_VERSION`).

---

## 🧪 Tests

The suite covers the parsers, quality gates and delivery logic. It touches neither the network nor Chromium, so it runs in about two seconds.

```bash
pip install -r requirements-dev.txt
python -m pytest
```

[`.github/workflows/tests.yml`](.github/workflows/tests.yml) runs it on every push and pull request.

---

---

## 🎨 Native WebGL Paper Shaders Carousel & Quality Control (QC)

AutoLinkedInPost compiles pixel-perfect, 4:5 vertical PDF carousels directly on-device using **Playwright Chromium**, **SwiftShader GPU acceleration**, and **Paper Shaders WebGL mesh gradients** (`@paper-design/shaders`):

1. **Native HTML/CSS & WebGL Pipeline (`src/carousel_renderer.py`):**
   * **Hardware-Free WebGL Rendering:** Runs headless Chromium with SwiftShader (`--use-gl=angle --use-angle=swiftshader --enable-webgl`) to render organic mesh gradients with analog film grain (`u_grainOverlay: 0.05`) without requiring dedicated GPU hardware.
   * **Deterministic Theme Rotation (`src/theme_manager.py`):** One coherent Refero theme per publication, derived from the UTC date and the repository name. No shared on-disk counter, so a fresh CI checkout still rotates.
   * **Pinned CDN Dependencies:** Lucide and Paper Shaders load at exact versions. With `@latest`, an upstream release could silently change the output of an unattended cron run.
   * **Deterministic Readiness Waits:** The exporter waits on explicit page signals (icons initialized, `document.fonts.ready` resolved, shaders mounted) instead of a fixed sleep, so a slow CDN degrades loudly rather than producing a half-rendered PDF.
   * **Zero Mobile PDF Glitches:** Strictly avoids blurred CSS `box-shadow` or `backdrop-filter`, preventing opaque black box artifacts in iOS PDFKit, Android PDF renderers, and Telegram.

2. **Two-Layer Quality Control (`src/pdf_evaluator.py`):**
   * **Layer 1 — Structural (0 tokens):** PyMuPDF verifies page count, 4:5 aspect ratio, empty pages, forbidden placeholders, safe-zone collisions and background color consistency. This is the layer that drives the self-healing loop, adjusting scale and theme.
   * **Layer 2 — Visual (multimodal):** Runs **once**, on the best structural candidate, rather than once per repair attempt. The loop also stops early when no repair action applies, since defects that come from the script cannot be fixed by re-rendering.
   * **Honest Reporting:** When the visual audit cannot run (no `GEMINI_API_KEY`), the result is reported as *structural only* instead of returning an approval nobody verified.

3. **Humanizer Anti-AI-Slop Engine (`src/humanizer_qc.py`):**
   * **24 AI Slop Patterns:** Audits every generated string (posts, comments, carousel scripts) to eliminate AI clichés, marketing buzzwords, formulaic binary contrasts, and rule-of-three adjective triples.
   * **Language-Aware Sanitizing:** Spanish and English keep separate replacement tables, so an English post never receives Spanish substitutions.
   * **Zero Clutter Telegram UX:** Directly attaches the compiled PDF ready to publish, completely removing verbose prompt text walls.

---

## 📂 Project Structure

```text
autolinkedinpost/
├── .github/workflows/
│   ├── daily_linkedin_post.yml # Daily GitHub Actions cron workflow
│   └── tests.yml               # Test suite on every push and pull request
├── .agents/skills/
│   ├── humanizer-zh/           # Humanizer anti-AI-slop skill rules & vocabulary
│   └── copywriting/            # Conversion copywriting frameworks, headlines & action CTAs
├── src/
│   ├── carousel_renderer.py    # Native 4:5 HTML/CSS & Paper Shaders WebGL PDF renderer
│   ├── theme_manager.py        # Refero design themes with deterministic date-based rotation
│   ├── pdf_evaluator.py        # Two-layer carousel QC (PyMuPDF structural + multimodal visual)
│   ├── humanizer_qc.py         # Humanizer Anti-AI-Slop Quality Control (QC) & auto-refinement
│   ├── llm_client.py           # Universal Multi-LLM client (Gemini, Claude, OpenAI, DeepSeek, Groq, Ollama)
│   ├── evaluator.py            # LLM-as-a-Judge quality gate with strict 1-5 rubric
│   ├── github_extractor.py     # Smart GitHub commit and event extraction with authorship filtering
│   ├── post_generator.py       # LinkedIn 2026 prompt engine (1st person singular & bilingual)
│   ├── repo_analyzer.py        # Deep repository analyzer (tree, README, tech stack)
│   └── telegram_notifier.py    # Clean HTML dispatcher with Tap-to-Copy blocks & direct PDF attachment
├── tests/                      # Test suite (parsers, quality gates, delivery)
├── bot.py                      # Interactive bot with concurrent threading & Render healthcheck
├── main.py                     # CLI runner for cron and local Multi-LLM runs
├── render.yaml                 # Infrastructure-as-code blueprint for Render
├── requirements.txt            # Production dependencies, bounded by major version
├── requirements-dev.txt        # Development and CI dependencies
├── pytest.ini                  # Test runner configuration
├── README.md                   # English technical documentation
└── README.es.md                # Spanish technical documentation
```

---

## 👨‍💻 License

Crafted with senior software architecture standards, clean modularity, and high observability.  
Distributed under the **MIT License**.

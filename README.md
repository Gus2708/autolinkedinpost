# 🚀 AutoLinkedInPost — Senior Engineering Content Engine (Multi-LLM 2026 Edition)

[🇺🇸 English Version](README.md) | [🇪🇸 Versión en Español](README.es.md)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Multi-LLM Ready](https://img.shields.io/badge/AI-Gemini%20%7C%20Claude%20%7C%20OpenAI%20%7C%20DeepSeek%20%7C%20Groq%20%7C%20Ollama-purple.svg)](https://github.com/Gus2708/autolinkedinpost)
[![Render Free 24/7](https://img.shields.io/badge/Deploy-Render%20Cloud-success.svg)](https://render.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**AutoLinkedInPost** is an autonomous engineering content automation engine built for senior software engineers, tech leads, and technical founders looking to establish technical authority with international recruiters and Engineering Managers on LinkedIn.

The engine continuously audits your real GitHub activity, extracts architectural design decisions, and produces complete publication packages optimized for the **LinkedIn 2026 Interest Graph** (Mobile-First 2-line paragraphs, 220-character hook cuts, save-driven CTAs, 10-slide Canva AI carousels, and clean first comments). All generated content is enforced through an automated **LLM-as-a-Judge Quality Gate** under a strict **Zero-Hallucination Grounding Policy** and powered by a universal **Multi-LLM Provider Architecture**.

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
               │     • 10-Slide Canva Script (Vertical 4:5 - 1200x1500) │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │         3. LLM-as-a-Judge Quality Gate (1-5 Rubric)    │
               │     • Factual Grounding (Strict Zero-Hallucination)    │
               │     • Hook Strength (< 220 chars before 'See more')    │
               │     • Mobile Readability & Save/CTA Factor             │
               │     └─► If Score < 4.0 ──► Auto-Refinement Loop        │
               └───────────────────────────┬────────────────────────────┘
                                           │
                                           ▼
               ┌────────────────────────────────────────────────────────┐
               │           4. Telegram Dispatcher & Interactive Bot     │
               │     • Native "Tap-to-Copy" Code Blocks (<pre>)         │
               │     • Interactive Paginated Repository Menu            │
               │     • Instant Bilingual Switch (English ⇄ Spanish)     │
               │     • Concurrent Threading (Zero-blocking UI)          │
               └────────────────────────────────────────────────────────┘
```

---

## 🧠 Multi-LLM Provider Architecture

The AI layer is completely decoupled using an agnostic Provider Pattern in [`src/llm_client.py`](file:///g:/Projects/autolinkedinpost/src/llm_client.py), allowing seamless model switching via standard environment variables:

| Provider | `LLM_PROVIDER` | API Key Variable | Recommended Models |
|---|---|---|---|
| **Google Gemini** *(Default)* | `gemini` | `GEMINI_API_KEY` | `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash` |
| **Anthropic Claude** | `anthropic` | `ANTHROPIC_API_KEY` | `claude-3-7-sonnet-20250219`, `claude-3-5-sonnet` |
| **OpenAI** | `openai` | `OPENAI_API_KEY` | `gpt-4o`, `gpt-4o-mini`, `o3-mini` |
| **DeepSeek** | `deepseek` | `DEEPSEEK_API_KEY` | `deepseek-chat`, `deepseek-reasoner` |
| **Groq** *(Ultra-fast inference)* | `groq` | `GROQ_API_KEY` | `llama-3.3-70b-versatile`, `mixtral-8x7b-32768` |
| **OpenRouter** | `openrouter` | `OPENROUTER_API_KEY` | `anthropic/claude-3.7-sonnet`, `meta-llama/llama-3.3-70b-instruct` |
| **Ollama** *(Local / Self-Hosted)* | `ollama` | `OLLAMA_BASE_URL` | `llama3.2`, `mistral`, `qwen2.5` |
| **Custom OpenAI-Compatible** | `custom` | `CUSTOM_LLM_API_KEY` | Endpoint at `CUSTOM_LLM_BASE_URL` (vLLM, LMStudio) |

> [!TIP]
> **Heuristic Auto-Detection:** If `LLM_PROVIDER` is omitted, the system automatically detects the provider based on the configured API key in your environment.

---

## ✨ Core Engineering Features

### 🎯 1. LinkedIn 2026 Algorithmic Optimization
- **High-Impact Hooks (< 220 characters):** Real technical tension or architectural trade-offs placed before the "See more" fold.
- **True Mobile-First Formatting:** Short 2 to 3-line paragraphs with mandatory whitespace for clean skimming on mobile screens.
- **Save-Focused CTAs (Saves > Likes):** CTAs engineered to trigger LinkedIn's "Suggested Content" algorithm multiplier (+60% reach boost).
- **First Comment Rule (60-minute window):** 100% clean post bodies without outbound links to avoid the 50% algorithmic link penalty; clean repo links are delivered in the seed comment.

### 🛡️ 2. Strict Zero-Hallucination Grounding
- **100% Factual Integrity:** Strictly forbidden from inventing fake metrics, non-existent production outages, or imaginary companies.
- **Architectural Authority:** When codebases lack explicit benchmark numbers, content focuses purely on real engineering problems, system design patterns (RAG, Outbox, CQRS, Caching), modularity, and trade-offs.

### 📑 3. Canva AI 10-Slide Carousel Model (24.4% Engagement)
- **4:5 Vertical Portrait (1200 x 1500 px):** Covers 35% more vertical viewport space on mobile devices than square or 16:9 widescreen formats.
- **10-Slide PAS Framework:** Problem, Agitation, Step-by-Step Solution, Before vs After, and Action CTA.
- **Canva Magic Studio Master Prompt:** Hardened prompt containing all pre-written slide texts and explicit negative prompts prohibiting 16:9 widescreen and placeholder domains (`reallygreatsite.com`).

### 🌐 4. Instant Bilingual Generation (English / Spanish)
- Interactive inline Telegram button (`🇬🇧 Generate in English` / `🇪🇸 Generate in Spanish`) allowing on-the-fly regeneration adapted to **US Tech Industry Standards** or native Spanish.

### 📱 5. Mobile UX with Native "Tap-to-Copy" Blocks
- All output in Telegram is delivered in isolated `<pre>` code blocks. A **single tap on iOS or Android** copies the exact clean block to your clipboard without dragging headers, emojis, or labels.

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

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment variables
Copy the template:
```bash
cp .env.example .env
```
Fill in your credentials:
```env
# AI Provider Configuration (gemini, openai, anthropic, deepseek, groq, openrouter, ollama)
LLM_PROVIDER=gemini
LLM_MODEL=gemini-3.7-flash

# API Key for the chosen provider
GEMINI_API_KEY="your_gemini_api_key"
# Or ANTHROPIC_API_KEY="sk-ant-..."
# Or OPENAI_API_KEY="sk-..."
# Or DEEPSEEK_API_KEY="sk-..."

# Telegram Bot
TELEGRAM_BOT_TOKEN="your_botfather_token"
TELEGRAM_CHAT_ID="your_telegram_numeric_id"

# GitHub
GH_USERNAME="your_github_username"
GH_TOKEN=""  # Optional GitHub PAT (required for private repositories)
LOOKBACK_DAYS=1
PYTHONIOENCODING=utf-8
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
   - 📑 **10-Slide Carousel Script + Canva AI Master Prompt**.
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

The project includes an embedded HTTP healthcheck daemon (`bot.py`) and a [`render.yaml`](file:///g:/Projects/autolinkedinpost/render.yaml) blueprint to run **24/7 at zero cost** on Render Web Services:

1. Push this repository to GitHub (can be **private**).
2. Go to your [Render Dashboard](https://dashboard.render.com/).
3. Click **New +** ➔ **Blueprint** (or **Web Service**) and select this repo.
4. Set the following environment variables in Render:
   - `LLM_PROVIDER`: `gemini` (or your preferred provider)
   - `GEMINI_API_KEY` (or the key for your active provider)
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `GH_USERNAME`
   - `GH_TOKEN` *(optional for private repos)*
   - `PYTHONIOENCODING`: `utf-8`
5. Done! The bot will listen 24/7 in the cloud without needing your computer running.

---

## ⏱️ Daily GitHub Actions Automation

The workflow [`.github/workflows/daily_linkedin_post.yml`](file:///g:/Projects/autolinkedinpost/.github/workflows/daily_linkedin_post.yml) runs daily at **21:00 UTC** (18:00 ARG / 15:00 CDMX). If no relevant commit activity occurred in the last 24 hours, the workflow exits silently without spamming.

To configure, add to **Settings ➔ Secrets and variables ➔ Actions**:
- `GEMINI_API_KEY` (or `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.)
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `GH_USERNAME`
- `GH_TOKEN` *(optional)*

---

## 📂 Project Structure

```text
autolinkedinpost/
├── .github/workflows/
│   └── daily_linkedin_post.yml # Daily GitHub Actions cron workflow
├── src/
│   ├── llm_client.py           # Universal Multi-LLM client (Gemini, Claude, OpenAI, DeepSeek, Groq, Ollama)
│   ├── evaluator.py            # LLM-as-a-Judge quality gate with strict 1-5 rubric
│   ├── github_extractor.py     # Smart GitHub commit and event extraction
│   ├── post_generator.py       # LinkedIn 2026 prompt engine (1st person singular & bilingual)
│   ├── repo_analyzer.py        # Deep repository analyzer (tree, README, tech stack)
│   └── telegram_notifier.py    # Chunked safe HTML dispatcher with Tap-to-Copy blocks
├── bot.py                      # Interactive bot with concurrent threading & Render healthcheck
├── main.py                     # CLI runner for cron and local Multi-LLM runs
├── render.yaml                 # Infrastructure-as-code blueprint for Render
├── requirements.txt            # Lightweight production dependencies
├── README.md                   # English technical documentation
└── README.es.md                # Spanish technical documentation
```

---

## 👨‍💻 License

Crafted with senior software architecture standards, clean modularity, and high observability.  
Distributed under the **MIT License**.

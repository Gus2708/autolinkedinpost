# Exploration: integrate-linkedin-skills

## Request Understanding
Integrate the complete \sergebulaev/linkedin-skills\ repository into \utolinkedinpost\ to build an end-to-end LinkedIn suite. The goal is to combine:
1. High-performing copy generation powered by 20 proven hook formulas (F1-F20), 2026 algorithm heuristics, and founder thought-leadership angles.
2. The existing automated 4:5 visual carousel rendering (Playwright + 6 design systems) and multi-tier quality control (\humanizer_qc.py\, \evaluator.py\, \pdf_evaluator.py\).
3. Automated LinkedIn operations including URL parsing, comment drafting, thread monitoring, audience analytics, and multi-backend publishing (Publora, Pixfaro, Apify, or copy-paste draft mode with approval gates).

## Current State
- \src/post_generator.py\: Generates LinkedIn post text and 10-slide carousel copy using Gemini/Multi-LLM based on GitHub repository activity.
- \src/humanizer_qc.py\ & \src/evaluator.py\: Enforce strict anti-AI-slop rules, metric grounding, and structural constraints.
- \src/carousel_renderer.py\ & \src/design_systems.py\: Render 4:5 slides into images/PDFs using Playwright with six design themes.
- \ot.py\ & \main.py\: Orchestrate GitHub extraction -> Post generation -> QC check -> Carousel render -> Telegram delivery.
- \	ests/\: 294 passing unit tests verifying carousel generation, design systems, LLM client, and quality gates (\python -m pytest\).
- Missing: Native LinkedIn API/Publora posting backend, URL parsing for existing LinkedIn threads, hook extraction from live URLs, comment drafting/reply workflows, audience analytics, and algorithm heuristic scoring.

## Affected Areas
| Area | Evidence | Why It Matters |
|------|----------|----------------|
| \.agents/skills/\ | \.agents/skills/\ currently contains only SDD skills, \copywriting\, and \humanizer-zh\ | Needs to register the 11 modular LinkedIn skills (\linkedin-post-writer\, \linkedin-comment-drafter\, \linkedin-humanizer\, etc.) |
| \src/linkedin/\ | Cloned \scratch/linkedin-skills/lib/\ containing clients and backends | Encapsulates external LinkedIn API adapters and backends into a clean package under \src/\ |
| \src/post_generator.py\ | Line 12-60: \SYSTEM_INSTRUCTION_ES\ and \SYSTEM_INSTRUCTION_EN\ | Needs integration of the 20 hook formulas, founder angles (A1-A10), and 2026 algorithm heuristics |
| \src/humanizer_qc.py\ | Line 1-250: Anti-slop checks and sanitizer | Needs extension with emoji density auditing and 2026 algorithm heuristics checks (dwell time, line spacing, link placement) |
| \ot.py\ / \main.py\ | Telegram-only delivery in \send_telegram_package\ | Can optionally support Publora/Pixfaro auto-publishing or human-in-the-loop approval when credentials are configured |
| equirements.txt\ | Current dependencies: \google-genai\, \playwright\, \pymupdf\, \pillow\, equests\, \python-dotenv\ | Validated against equests\ and optional backend dependencies (all light and compatible) |

## Existing Tests
| Test/File | Relevance | Missing Coverage |
|-----------|-----------|------------------|
| \	ests/test_quality_gates.py\ | Validates post evaluator and humanizer QC rules | Needs test coverage for new algorithm heuristics, emoji density checks, and hook validation |
| \	ests/test_carousel.py\ | Covers carousel rendering, CSS layouts, and PDF compilation | No changes needed, existing tests serve as regression safety net |
| \	ests/test_llm_client.py\ | Mocks and tests LLM prompt/response handling | Needs coverage for new prompt templates using hook formulas |
| \	ests/test_bot.py\ | Tests end-to-end bot execution loop | Needs coverage for optional LinkedIn publishing branch |
| \	ests/test_linkedin_suite.py\ | Does not exist yet | Must cover URL parsing, backend selector, Publora/Pixfaro client adapters, and approval flow with mocks |

## Options
| Option | Pros | Cons | Risk | Effort |
|--------|------|------|------|--------|
| **Option 1: Flat Direct Copy**<br>Copy all scripts from \linkedin-skills\ into \lib/\ and paste reference docs into root | Minimal file renaming | Violates clean architecture; mixes CLI scripts with bot core; hard to test; pollutes repo root | High | Low |
| **Option 2: Modular Architecture Integration (Recommended)**<br>1. Register all 11 skills in \.agents/skills/linkedin-*\<br>2. Centralize references in \docs/references/\<br>3. Implement clean package \src/linkedin/\ with clients, parsers, and approval gates<br>4. Enhance \post_generator.py\ & \humanizer_qc.py\ with hook formulas & algorithm heuristics<br>5. Connect publisher to \ot.py\ with mockable tests | Clean Hexagonal architecture; 100% backward compatible with existing bot and carousels; testable with pytest unit tests; full agent skill discovery | Low | Medium |

## Recommendation
Adopt **Option 2**. It cleanly integrates the skills and reference knowledge into the agent brain while refactoring the client libraries into a robust \src/linkedin/\ package that seamlessly plugs into \utolinkedinpost\ existing QC and carousel pipeline.

## Risks
- **External API dependency**: Publora, Pixfaro, or Apify APIs might be unavailable or lack API keys in local development. *Mitigation*: Fall back to Tier 0 (Draft mode) by default, using human approval and copy-paste output when API keys are absent.
- **Dependency bloat**: Ensuring no conflicting dependencies. *Mitigation*: The \linkedin-skills\ lib only requires standard equests\ and Python standard library, which are already present in equirements.txt\.
- **Regression in QC / Carousels**: *Mitigation*: Retain strict TDD; keep existing 294 tests passing on every change.

## Open Questions
- None blocking. Tier 0 (draft mode) is the default when \PUBLORA_API_KEY\ is not present, allowing full local and CI execution without external API accounts.

## Ready For Planning
Yes. The codebase seam is cleanly identified in \src/linkedin/\, \src/post_generator.py\, \src/humanizer_qc.py\, and \.agents/skills/\.

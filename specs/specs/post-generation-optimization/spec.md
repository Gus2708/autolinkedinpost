# Spec: post-generation-optimization

## Domain Overview
Domain behavior synchronized from change artifacts.

## Requirements

### Requirement: post-generation-optimization/hook-selection — 20 Hook Formulas and Founder Angles
The system MUST support injecting any of the 20 hook formulas (F1 to F20) and 10 founder angles (A1 to A10) into post generation prompts.

#### Scenario: Generate post with specific hook formula
- GIVEN a prompt request configured with hook formula F1 or founder angle A1
- WHEN \generate_linkedin_post\ prepares the prompt
- THEN the prompt instruction mandates opening the post according to the specified formula structure.

### Requirement: post-generation-optimization/algorithm-heuristics — 2026 Algorithmic Compliance
The system MUST structure post content to comply with 2026 dwell-time and link-placement heuristics.

#### Scenario: Keep external links out of main hook body
- GIVEN post text generation
- WHEN the post copy is emitted
- THEN external links are placed in the closing section or deferred to comments rather than embedded in the opening hook lines.

### Requirement: post-generation-optimization/anti-ai-directives — No AI Slop Prompt Integration
The system MUST include strict no-ai-slop directives in generation system prompts and prompt templates for both Spanish and English:
1. Ban binary contrasts ("It's not X. It's Y.", "No se trata de X, sino de Y").
2. Ban faux-insight setups ("What nobody tells you", "The part everyone misses", "Lo que nadie te cuenta").
3. Ban colon reveals ("The secret: ...", "El detalle clave: ...").
4. Ban superficial analysis with trailing gerunds ("highlighting...", "underscoring...", "destacando...").
5. Ban fake-profound kickers and summary-recap endings ("In conclusion", "Ultimately", "En resumen").
6. Ban outright buzzwords and filler phrases (delve, leverage, foster, streamline, robust, cutting-edge, tapestry, game changer, apalancar, vanguardista, etc.).

#### Scenario: Post prompt includes no-ai-slop system directives
- GIVEN prompt construction in `src/post_generator.py`
- WHEN `SYSTEM_INSTRUCTION_ES` or `SYSTEM_INSTRUCTION_EN` is inspected
- THEN it explicitly includes prohibitions against faux-insight setups, colon reveals, trailing gerund analysis, and banned words.

### Requirement: post-generation-optimization/portability-test — Portability Test Enforcement
The system MUST enforce the portability test: if a sentence or claim could be moved unchanged to another company, product, or stack, it must be rejected or replaced with specific engineering mechanisms, metrics, or architectural trade-offs.

#### Scenario: Prompt template mandates portability rule
- GIVEN `PROJECT_PROMPT_TEMPLATE_ES` and `PROJECT_PROMPT_TEMPLATE_EN`
- WHEN the prompt is formatted for LLM generation
- THEN it instructs the model to subject every sentence to the portability test and reject generic filler.

# Intent: integrate-no-ai-slop

## Context
The repository `petergyang/no-ai-slop` specifies 20+ patterns of AI slop, words to cut, and evaluation rubrics (`eval.md`) to strip artificial AI writing patterns without flattening personal human voice.
Currently, `autolinkedinpost` has initial anti-slop rules in `src/humanizer_qc.py` (24 patterns based on classic WikiProject AI Cleanup) and high-level rules in `src/post_generator.py`. However, it lacks detection for key modern slop patterns identified by Peter Yang:
- Faux-insight setups ("What nobody tells you", "The part everyone misses", "Lo que nadie te cuenta")
- Colon reveals (fake drama lowercase reveal after a noun phrase and colon)
- Superficial analysis with trailing gerunds ("highlighting...", "underscoring...", "destacando...")
- Importance puffery and interpretive metadiscourse ("That last part matters more than it sounds")
- Weasel attribution ("experts agree", "studies show", "estudios demuestran")
- Rhetorical setups ("What if I told you...", "Think about it:")
- Fake-profound kickers and summary-recap endings ("In conclusion", "Ultimately")
- The Portability Test ("if a sentence could apply unchanged to another company/stack, cut it")
- The expanded banned word and empty adverb catalogs (delve, leverage, foster, streamline, robust, cutting-edge, paradigm shift, game changer, tapestry, realm, beacon, multifaceted, meticulous, intricate, paramount, transformative, elevate, embark, supercharge, harness, ever-evolving).

## Desired Outcome
Integrate `no-ai-slop` holistically into `autolinkedinpost`:
1. **Post Generation**: Update system instructions and prompt templates (`src/post_generator.py`) in both Spanish and English with the complete `no-ai-slop` negative constraints, portability test, and active-voice directives.
2. **Quality Control (QC)**: Expand deterministic sanitization and heuristic detection in `src/humanizer_qc.py` to audit and catch all 20+ slop patterns in both languages, returning precise violation snippets and actionable replacement advice.
3. **LLM Humanizer Rewriting**: Update the Humanizer LLM system prompt in `src/humanizer_qc.py` with the 4-phase `no-ai-slop` evaluation rubric, ensuring rewrites retain the writer's authentic technical edge while eliminating slop.
4. **Documentation & References**: Synchronize `docs/references/voice-rules.md` and `docs/references/voice-profile.md` with the new standards.
5. **Strict TDD & Regression Safety**: Full test coverage verifying all new patterns with 100% pass rate across the entire test suite.

## Scope
### In Scope
- **Post Generation Prompts (`src/post_generator.py`)**:
  - Update `SYSTEM_INSTRUCTION_ES` and `SYSTEM_INSTRUCTION_EN`.
  - Update `PROJECT_PROMPT_TEMPLATE_ES` and `PROJECT_PROMPT_TEMPLATE_EN` with the Portability Test and strict anti-slop rules.
- **Quality Control Engine (`src/humanizer_qc.py`)**:
  - Expand `SLOP_PATTERNS_ES` and `SLOP_PATTERNS_EN` with faux-insight setups, colon reveals, superficial trailing gerunds, importance puffery, metadiscourse, weasel attribution, rhetorical setups, fake-profound kickers, summary recaps, and banned vocabulary.
  - Expand `REPLACEMENTS_ES` and `REPLACEMENTS_EN` for deterministic sanitization.
  - Upgrade `HUMANIZER_REWRITE_SYSTEM` prompt with the full `no-ai-slop` editing checklist.
- **Documentation (`docs/references/`)**:
  - Sychronize `voice-rules.md` and `voice-profile.md` with `no-ai-slop` patterns.
- **Tests (`tests/`)**:
  - Add comprehensive unit tests in `tests/test_humanizer_qc.py` and `tests/test_post_generator.py` covering all new patterns and prompts.

### Out of Scope
- Modifying Telegram notification handlers or approval callback payloads.
- Changing the WebGL / Playwright carousel graphics rendering pipeline.
- Modifying external publishing backends (Publora / Pixfaro).

## Key Decisions
- **Bilingual Parity**: Ensure every English slop pattern has an idiomatic, battle-tested Spanish equivalent regex pattern and replacement suggestion.
- **Portability Test as a First-Class Generation Rule**: Prompt templates will explicitly instruct the model to test every sentence for portability and replace generic fluff with real metrics and code artifacts.
- **Normalized Pattern Density Scoring**: Preserve the calibrated score formula in `audit_text_humanizer_qc` so that long technical posts are scored by violation density rather than punitive raw count.
- **Strict Backward Compatibility**: Preserve the existing interface signatures of `audit_text_humanizer_qc`, `audit_full_package_qc`, `sanitize_text_humanizer`, and `generate_linkedin_post`.

## Success Criteria
- [ ] `SLOP_PATTERNS_ES` and `SLOP_PATTERNS_EN` in `src/humanizer_qc.py` detect faux-insight setups, colon reveals, superficial gerunds, importance puffery, metadiscourse, weasel attribution, rhetorical setups, fake-profound kickers, and banned words.
- [ ] `sanitize_text_humanizer` cleans expanded banned words and fillers in ES and EN without altering technical code terms.
- [ ] `SYSTEM_INSTRUCTION_ES` and `SYSTEM_INSTRUCTION_EN` in `src/post_generator.py` mandate `no-ai-slop` directives.
- [ ] `PROJECT_PROMPT_TEMPLATE_ES` and `PROJECT_PROMPT_TEMPLATE_EN` mandate the Portability Test and radical specificity.
- [ ] `HUMANIZER_REWRITE_SYSTEM` reflects `no-ai-slop` editing principles.
- [ ] Reference docs `docs/references/voice-rules.md` and `docs/references/voice-profile.md` are updated.
- [ ] All new unit tests pass with strict TDD, and the full regression suite (356+ tests) passes with 0 failures.

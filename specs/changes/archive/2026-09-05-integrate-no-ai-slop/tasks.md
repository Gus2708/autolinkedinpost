# Tasks: integrate-no-ai-slop

## Review Workload Forecast
Estimated changed lines: 250-400
Estimated product files: 4-6
Target budget: 800 lines, 15 files
Hard limit: 1000 lines, 25 files
Budget risk: Low
Independent slices possible: No
Shared production files across slices: No
Forecast basis: brief intent, delta specs, and analysis of petergyang/no-ai-slop against humanizer_qc.py, post_generator.py, and voice references

## Delivery Plan
Strategy: single-pr
Model: whole
PR mode: draft
PR creation point: final verify only
Current delivery unit: whole

### Whole Delivery
Planned branch/base: sdd/integrate-no-ai-slop -> main
Scope: Integration of 20+ no-ai-slop patterns into heuristic QC, deterministic sanitization, LLM rewriter prompt, post generation system instructions, prompt templates, and voice reference documentation.

## Slice: whole — Integrate No-AI-Slop

### Phase 1: QC Heuristic Detection & Deterministic Sanitization
- [x] 1.1 Extend banned vocabulary and empty filler detection in `src/humanizer_qc.py`
  - [x] 1.1.a Establish safety net verifying existing `SLOP_PATTERNS_ES` and `SLOP_PATTERNS_EN` behavior
  - [x] 1.1.b Author failing tests in `tests/test_humanizer_qc.py` for new banned words (delve, leverage, foster, streamline, cutting-edge, supercharge, apalancar, vanguardista, potenciar cliché)
  - [x] 1.1.c Implement expanded banned vocabulary regex in `src/humanizer_qc.py`
  - [x] 1.1.d Triangulate detection across ES and EN with mixed casing and punctuation
  - [x] 1.1.e Refactor pattern definitions with modular category grouping

- [x] 1.2 Implement structural slop patterns from no-ai-slop
  - [x] 1.2.a Establish safety net for existing structural pattern violations (binary contrast, triads, greetings)
  - [x] 1.2.b Author failing tests for faux-insight setups, colon reveals, superficial trailing gerunds, importance puffery, metadiscourse, weasel attribution, rhetorical setups, and fake-profound kickers
  - [x] 1.2.c Implement regex and heuristic detectors in `src/humanizer_qc.py`
  - [x] 1.2.d Triangulate edge cases: legitimate colons (code, lists), normal gerunds vs trailing analysis clauses
  - [x] 1.2.e Refactor audit reporting to provide concise, actionable suggestions

- [x] 1.3 Extend deterministic sanitization in `src/humanizer_qc.py`
  - [x] 1.3.a Establish safety net for existing `sanitize_text_humanizer` replacements
  - [x] 1.3.b Author failing tests for deterministic cleanup of newly banned terms and fillers
  - [x] 1.3.c Update `REPLACEMENTS_ES` and `REPLACEMENTS_EN` in `src/humanizer_qc.py`
  - [x] 1.3.d Triangulate sanitization to guarantee technical code terms, imports, and repo names remain uncorrupted
  - [x] 1.3.e Refactor replacement passes for optimal single-pass execution

### Phase 2: Post Generator System Instructions & Templates
- [x] 2.1 Update system instructions with no-ai-slop rules in `src/post_generator.py`
  - [x] 2.1.a Establish safety net verifying current system instruction constants
  - [x] 2.1.b Author failing tests verifying `SYSTEM_INSTRUCTION_ES` and `SYSTEM_INSTRUCTION_EN` include no-ai-slop rules (faux-insight bans, colon reveal bans, trailing gerund bans)
  - [x] 2.1.c Update `SYSTEM_INSTRUCTION_ES` and `SYSTEM_INSTRUCTION_EN` in `src/post_generator.py`
  - [x] 2.1.d Triangulate prompt construction with both Spanish and English generation targets
  - [x] 2.1.e Refactor instruction blocks for clarity and token efficiency

- [x] 2.2 Enforce Portability Test and anti-slop constraints in prompt templates
  - [x] 2.2.a Establish safety net verifying existing `PROJECT_PROMPT_TEMPLATE_ES` and `PROJECT_PROMPT_TEMPLATE_EN`
  - [x] 2.2.b Author failing tests for presence of Portability Test and anti-slop constraints in prompt templates
  - [x] 2.2.c Update prompt templates in `src/post_generator.py`
  - [x] 2.2.d Triangulate template rendering with sample commit messages and repo metadata
  - [x] 2.2.e Refactor template formatting and section headers

### Phase 3: LLM Humanizer Rewriter, References & Full Verification
- [x] 3.1 Update LLM Humanizer rewrite prompt in `src/humanizer_qc.py`
  - [x] 3.1.a Establish safety net for `HUMANIZER_REWRITE_SYSTEM` prompt structure
  - [x] 3.1.b Author failing tests checking `HUMANIZER_REWRITE_SYSTEM` incorporates `no-ai-slop` editing principles and eval rubric
  - [x] 3.1.c Update `HUMANIZER_REWRITE_SYSTEM` in `src/humanizer_qc.py`
  - [x] 3.1.d Triangulate LLM humanizer prompt formatting with simulated QC violation feedback
  - [x] 3.1.e Refactor prompt composition helper

- [x] 3.2 Update reference documentation
  - [x] 3.2.a Establish safety net checking `docs/references/voice-rules.md` and `docs/references/voice-profile.md`
  - [x] 3.2.b Update `docs/references/voice-rules.md` with the 20+ `no-ai-slop` pattern catalog
  - [x] 3.2.c Update `docs/references/voice-profile.md` with the Portability Test and minimum effective edit principles
  - [x] 3.2.d Triangulate documentation cross-references
  - [x] 3.2.e Refactor formatting in docs references

- [x] 3.3 End-to-end integration and regression suite verification
  - [x] 3.3.a Establish safety net running baseline test suite
  - [x] 3.3.b Author failing test in tests/test_post_generator.py and tests/test_humanizer_qc.py for end-to-end pipeline compliance
  - [x] 3.3.c Implement end-to-end integration test passes
  - [x] 3.3.d Triangulate with mock posts in English and Spanish across edge case inputs
  - [x] 3.3.e Refactor test suite fixtures and helper functions

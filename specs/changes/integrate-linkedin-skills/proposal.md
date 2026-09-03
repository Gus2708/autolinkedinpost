# Proposal: integrate-linkedin-skills

## Intent
Transform utolinkedinpost into a comprehensive LinkedIn growth and management suite by integrating sergebulaev/linkedin-skills. The current repository excels at commit-driven post generation, anti-slop QC, and 4:5 visual carousel rendering via Playwright, but lacks LinkedIn platform integration, live URL parsing, hook extraction, comment/reply handling, audience analytics, and multi-backend publishing (Publora/Pixfaro/Apify). Integrating these capabilities enables both end-to-end automated posting and interactive LinkedIn community management under strict quality gates.

## Scope
### In Scope
- Registering all 11 LinkedIn skills in .agents/skills/linkedin-* with centralized reference documentation in docs/references/ and .agents/skills/references/.
- Implementing the src/linkedin/ module containing:
  - url_parser.py: Parsing LinkedIn post/comment URLs and extracting URNs.
  - ackends.py & client adapters: Multi-backend publishing with Publora, Pixfaro, and local copy-paste Tier 0 fallback.
  - pproval.py: Human-in-the-loop draft/review/publish approval gate.
- Updating src/post_generator.py to integrate the 20 viral hook formulas (F1-F20), 2026 algorithm heuristics, and founder thought-leadership angles (A1-A10).
- Extending src/humanizer_qc.py with emoji density checks and 2026 algorithmic compliance rules.
- Providing full test coverage in 	ests/test_linkedin_suite.py and ensuring all existing 294 tests continue to pass.

### Out of Scope
- Mandatory paid external API keys: All features must run in Tier 0 (Draft mode) when PUBLORA_API_KEY or APIFY_API_KEY are absent.
- Rewriting the Playwright carousel engine or existing design systems.

## Capabilities
### New Capabilities
- linkedin-skills-ecosystem: Provision of 11 agent skills and 8 reference guides for interactive LinkedIn workflows (comment drafting, post auditing, hook extraction, thread monitoring, advocacy).
- linkedin-integration-engine: Python-native URL parsing, multi-backend publishing adapter, and human-in-the-loop approval mechanism in src/linkedin/.
- post-generation-optimization: Integration of 20 hook formulas, 2026 algorithm heuristics, and founder angles into src/post_generator.py.
- nti-ai-quality-gates: Enhancement of src/humanizer_qc.py to audit emoji density and algorithmic heuristics alongside existing anti-slop rules.

### Modified Capabilities
- None.

## Approach
Follow Option 2 (Modular Architecture Integration):
1. Ingest the 11 skills into .agents/skills/linkedin-* and documentation into docs/references/.
2. Refactor client libraries into a clean, testable src/linkedin/ package with dependency injection for HTTP calls to allow full unit test mocking.
3. Augment system prompts and prompt templates in src/post_generator.py to reference hook formulas and algorithmic rules cleanly.
4. Add emoji density scoring and heuristic validation functions to src/humanizer_qc.py.
5. Maintain strict TDD: write failing unit tests in 	ests/test_linkedin_suite.py before implementing each component.

## Affected Areas
| Area | Impact | Description |
|------|--------|-------------|
| .agents/skills/ | High | Adds 11 skills and references for agent execution |
| docs/references/ | Medium | Ingests 8 LinkedIn algorithmic and voice reference guides |
| src/linkedin/ | High | New core package for URL parsing, backend selector, and publishing |
| src/post_generator.py | Medium | Incorporates hook formulas (F1-F20) and founder angles |
| src/humanizer_qc.py | Medium | Extends anti-slop gate with emoji density and format heuristics |
| 	ests/test_linkedin_suite.py | High | New test suite verifying all new Python components |

## Risks
| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Missing external credentials break CI or local runs | Low | Enforce Tier 0 fallback (Draft mode) by default when environment variables are unset |
| Regressions in existing carousel rendering or QC | Low | Run full python -m pytest suite on every TDD cycle |
| Prompt bloat causing high token usage | Medium | Structure hook formulas and heuristics modularly and pass only selected formulas per post style |

## Rollback Plan
If regressions occur, remove src/linkedin/, revert modifications to src/post_generator.py and src/humanizer_qc.py, and remove newly added skills from .agents/skills/. Existing tests and git commit history guarantee a clean return to the prior working state.

## Success Criteria
- [ ] All 11 LinkedIn skills are discoverable in .agents/skills/ with valid frontmatter.
- [ ] src/linkedin/ correctly parses LinkedIn post and comment URLs and manages publishing backends with approval gates.
- [ ] Post generator supports selectable hook formulas (F1-F20) and 2026 algorithm heuristics.
- [ ] Humanizer QC detects and flags excessive emoji density (>3 emojis) and heuristic violations.
- [ ] Comprehensive unit tests in 	ests/test_linkedin_suite.py pass with 100% mocked external calls.
- [ ] All existing 294 tests continue to pass without error.

## Open Questions
- None.

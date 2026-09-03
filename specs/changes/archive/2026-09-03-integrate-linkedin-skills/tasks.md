# Tasks: integrate-linkedin-skills

## Review Workload Forecast
Estimated changed lines: 350-500 lines
Estimated product files: 8-12 files
Target budget: 800 lines, 15 files
Hard limit: 1000 lines, 25 files
Budget risk: Low
Independent slices possible: No
Shared production files across slices: Yes
Forecast basis: proposal, specs, and design for integrate-linkedin-skills

## Delivery Plan
Strategy: single-pr
Model: whole
PR mode: draft
PR creation point: final verify only
Current delivery unit: whole

### Whole Delivery
Planned branch/base: sdd/integrate-linkedin-skills -> main
Scope: Ingest 11 LinkedIn skills, integrate src/linkedin package, enhance post_generator and humanizer_qc, add tests/test_linkedin_suite.py.

## Slice: whole — Complete LinkedIn Skills Suite Integration

### Phase 1: Core URL Parsing, Approval Gate, and Hook Registry
- [x] 1.1 Implement LinkedIn URL parsing and URN extraction
  - [x] 1.1.a Run pytest safety net
  - [x] 1.1.b Write failing test for post and comment URL parsing in tests/test_linkedin_suite.py
  - [x] 1.1.c Implement parse_linkedin_url in src/linkedin/url_parser.py
  - [x] 1.1.d Triangulate with permalink and malformed URL cases
  - [x] 1.1.e Refactor regex patterns and type hints cleanly
- [x] 1.2 Implement human approval gate state machine
  - [x] 1.2.a Run pytest safety net
  - [x] 1.2.b Write failing test for ApprovalGate states in tests/test_linkedin_suite.py
  - [x] 1.2.c Implement ApprovalGate in src/linkedin/approval.py
  - [x] 1.2.d Triangulate with confirm, reject, and re-entry transitions
  - [x] 1.2.e Clean up enum representations
- [x] 1.3 Implement viral hook formulas and founder angles registry
  - [x] 1.3.a Run pytest safety net
  - [x] 1.3.b Write failing test for hook catalog access in tests/test_linkedin_suite.py
  - [x] 1.3.c Implement HOOK_FORMULAS and FOUNDER_ANGLES in src/linkedin/hooks.py
  - [x] 1.3.d Triangulate by asserting formulas F1-F20 and angles A1-A10 coverage
  - [x] 1.3.e Refactor registry helpers

### Phase 2: Publishing Backend Adapters and Fallback
- [x] 2.1 Implement multi-backend publishing adapter with Tier 0 draft fallback
  - [x] 2.1.a Run pytest safety net
  - [x] 2.1.b Write failing test for BackendSelector and Publora client mocking in tests/test_linkedin_suite.py
  - [x] 2.1.c Implement PubloraClient, PixfaroClient, and BackendSelector in src/linkedin/backends.py and src/linkedin/clients/
  - [x] 2.1.d Triangulate with Tier 0 fallback when PUBLORA_API_KEY is unset
  - [x] 2.1.e Refactor client session handling and exports in src/linkedin/__init__.py

### Phase 3: Post Generation and Humanizer QC Enhancement
- [x] 3.1 Enhance post generator with hook formula parameters and 2026 heuristics
  - [x] 3.1.a Run pytest safety net
  - [x] 3.1.b Write failing test verifying hook injection in tests/test_linkedin_suite.py
  - [x] 3.1.c Update src/post_generator.py to support hook formula selection and algorithmic constraints
  - [x] 3.1.d Triangulate with default vs explicit hook parameters
  - [x] 3.1.e Refactor prompt assembly
- [x] 3.2 Add emoji density and algorithmic heuristic audits to humanizer QC
  - [x] 3.2.a Run pytest safety net
  - [x] 3.2.b Write failing test for audit_emoji_density and audit_algorithm_heuristics in tests/test_linkedin_suite.py
  - [x] 3.2.c Implement audit_emoji_density and audit_algorithm_heuristics in src/humanizer_qc.py
  - [x] 3.2.d Triangulate with 0, 3, and 5 emoji cases and opening link checks
  - [x] 3.2.e Refactor unicode detection and error reporting

### Phase 4: Skills and Reference Documentation Registration
- [x] 4.1 Ingest 11 modular LinkedIn skills and reference guides
  - [x] 4.1.a Run pytest safety net
  - [x] 4.1.b Write verification test checking presence of all 11 skills in .agents/skills/ and 8 references
  - [x] 4.1.c Copy skills and reference files into .agents/skills/ and docs/references/
  - [x] 4.1.d N/A — file copy and markdown assets do not require behavioral triangulation
  - [x] 4.1.e Verify frontmatter and links in registered skills

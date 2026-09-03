# Design: integrate-linkedin-skills

## Technical Approach
Integrate `sergebulaev/linkedin-skills` using a clean Ports & Adapters (Hexagonal) architecture that separates operational skills, API client adapters, and content generation pipelines.
1. **Agent Skills Layer**: Copy the 11 modular skills into `.agents/skills/linkedin-*` and place shared references into `docs/references/` and `.agents/skills/references/`.
2. **Platform Integration Engine (`src/linkedin/`)**:
   - `url_parser.py`: Parse LinkedIn post and comment URLs and extract canonical URNs.
   - `approval.py`: Enforce human-in-the-loop approval before any network mutation.
   - `backends.py`: Multi-backend selector supporting Publora, Pixfaro, and a zero-dependency Tier 0 (Draft) fallback.
   - `clients/`: Dedicated HTTP clients with session injection for testing.
   - `hooks.py`: Programmatic registry of 20 viral hook formulas (F1-F20) and 10 founder angles (A1-A10).
3. **Core Pipeline Enhancement**:
   - Augment `src/post_generator.py` to optionally parameterize prompt construction with selected hook formulas.
   - Augment `src/humanizer_qc.py` with `audit_emoji_density` (max 3 emojis) and `audit_algorithm_heuristics` (avoid external links in opening lines).
4. **Strict TDD & Regression Safety Net**: Implement comprehensive unit tests in `tests/test_linkedin_suite.py` mocking all remote HTTP traffic, preserving all 294 existing tests.

## Architecture Decisions
| Decision | Choice | Alternatives | Rationale |
|----------|--------|--------------|-----------|
| Library Placement | New package `src/linkedin/` | Flat scripts in `lib/` or root | Preserves clean project structure under `src/` and keeps existing imports intact |
| Publishing Default | Tier 0 (Draft mode) | Hard requirement on Publora API key | Guarantees local runs, offline testing, and CI pipelines succeed without third-party API keys |
| HTTP Client Design | Dependency-injected `requests.Session` | Global requests calls or Playwright scraping | Enables deterministic mocking in pytest without network dependency |
| Hook Registry | Python dictionary/dataclass in `src/linkedin/hooks.py` | Reading raw markdown files at runtime | Zero filesystem overhead during LLM prompt generation and strongly typed formula validation |

## Architecture Design

### Project Placement
```text
src/
├── linkedin/
│   ├── __init__.py
│   │   └── exports
            [new] Public package exports for url_parser, backends, clients, and approval
│   ├── url_parser.py
│   │   └── parse_linkedin_url()
            [new] Parse LinkedIn post and comment URLs and extract URNs
│   ├── approval.py
│   │   └── ApprovalGate
            [new] Manage human approval state for draft publication
│   ├── hooks.py
│   │   └── get_hook_formula()
            [new] Access 20 hook formulas and 10 founder angles
│   ├── backends.py
│   │   └── BackendSelector
            [new] Select active publishing backend with Tier 0 fallback
│   └── clients/
│       ├── publora.py
│       │   └── PubloraClient
                [new] Client for Publora publishing API
│       └── pixfaro.py
│           └── PixfaroClient
                [new] Client for Pixfaro publishing API
├── post_generator.py
│   └── generate_linkedin_post()
        [modify] Support hook formula selection and 2026 heuristics
└── humanizer_qc.py
    ├── audit_emoji_density()
        [new] Audit post text for maximum 3 emojis
    └── audit_algorithm_heuristics()
        [new] Audit post text for opening link penalties and dwell-time formatting
tests/
└── test_linkedin_suite.py
    ├── test_url_parser()
        [new] Test valid and invalid LinkedIn URL parsing
    ├── test_approval_gate()
        [new] Test approval state machine transitions
    ├── test_backend_selector()
        [new] Test Publora dispatch and Tier 0 fallback
    ├── test_hooks_registry()
        [new] Test formula retrieval and formatting
    ├── test_emoji_density()
        [new] Test emoji count validation
    └── test_algorithm_heuristics()
        [new] Test link penalty detection
```

### Data Flow
1. **URL Input & Extraction**: User provides LinkedIn URL -> `url_parser.py` extracts `post_urn` and `comment_id`.
2. **Drafting & Generation**: `post_generator.py` retrieves formula from `hooks.py` -> LLM client generates copy adhering to 2026 heuristics.
3. **Quality Control**: `humanizer_qc.py` runs anti-slop rules, metric grounding checks, `audit_emoji_density()`, and `audit_algorithm_heuristics()`.
4. **Approval**: Draft presented to user -> `ApprovalGate` requires explicit confirmation before progressing.
5. **Publishing**: `BackendSelector` dispatches to `PubloraClient` / `PixfaroClient` if keys exist, or formats Tier 0 copy-paste block if in draft mode.

### Interfaces / Contracts
```python
# url_parser.py
def parse_linkedin_url(url: str) -> Optional[Dict[str, Optional[str]]]:
    pass

# approval.py
class ApprovalStatus(Enum):
    PENDING = 'pending'
    APPROVED = 'approved'
    REJECTED = 'rejected'

class ApprovalGate:
    def request_approval(self, draft_id: str, content: str) -> ApprovalStatus: pass
    def confirm(self, draft_id: str) -> None: pass
    def reject(self, draft_id: str) -> None: pass
    def is_approved(self, draft_id: str) -> bool: pass

# backends.py
class BackendSelector:
    def __init__(self, publora_client=None, pixfaro_client=None): pass
    def publish(self, text: str, media_urls: Optional[List[str]] = None) -> Dict[str, Any]: pass

# humanizer_qc.py
def audit_emoji_density(text: str, max_emojis: int = 3) -> Tuple[bool, int, str]: pass
def audit_algorithm_heuristics(text: str) -> Tuple[bool, List[str]]: pass
```

## Testing Strategy
| Layer | What | Approach |
|-------|------|----------|
| Unit | `url_parser` | Test standard post URLs, comment permalinks, activity URNs, and garbage inputs |
| Unit | `approval` | Test state transitions (pending -> approved, pending -> rejected, double confirmation) |
| Unit | `backends` & `clients` | Test Publora/Pixfaro API payloads, HTTP error handling, and Tier 0 draft fallback with `unittest.mock` |
| Unit | `hooks` | Verify all 20 formulas and 10 founder angles load with valid metadata |
| Unit | `humanizer_qc` extensions | Verify emoji counting across Unicode ranges and opening link detection |
| Integration / Regression | Full test suite | Run `python -m pytest` ensuring all existing 294 tests pass untouched |

## Migration / Rollout
1. Copy skills and documentation into workspace paths (`.agents/skills/`, `docs/references/`).
2. Add `src/linkedin/` package without breaking existing imports.
3. Extend `post_generator.py` and `humanizer_qc.py` with backward-compatible default parameters.
4. Run full test suite in CI.

## Technical Risks
| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Remote API downtime or rate limit | Low | All tests mock network calls; Tier 0 fallback ensures operational continuity |
| Emoji regex missing complex Unicode sequences | Low | Use standard Unicode emoji properties or character classification helper |
| Existing QC false positives on technical text | Low | Heuristics focus specifically on external URLs in lines 1-3 and emoji counts, not code tokens |

## Open Questions
- None.

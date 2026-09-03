# Delta Spec: anti-ai-quality-gates

## ADDED Requirements

### Requirement: anti-ai-quality-gates/emoji-density — Emoji Density Audit
The system MUST audit emoji density and flag any post exceeding 3 emojis.

#### Scenario: Flag post with excessive emojis
- GIVEN a draft post containing more than 3 emojis
- WHEN \udit_emoji_density\ is executed
- THEN it returns a failed check reporting the emoji count and a maximum threshold of 3.

#### Scenario: Pass post with compliant emoji count
- GIVEN a draft post containing between 0 and 3 emojis
- WHEN \udit_emoji_density\ is executed
- THEN it returns a pass status with zero violations.

### Requirement: anti-ai-quality-gates/heuristic-audit — 2026 Algorithmic Heuristics Audit
The system MUST audit post text for algorithmic penalties including external links in the first 3 lines.

#### Scenario: Detect link penalty in opening lines
- GIVEN a draft post containing an external HTTP URL in lines 1 to 3
- WHEN \udit_algorithm_heuristics\ is executed
- THEN it returns a violation instructing link relocation to preserve reach.

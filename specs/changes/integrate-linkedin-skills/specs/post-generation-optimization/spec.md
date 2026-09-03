# Delta Spec: post-generation-optimization

## ADDED Requirements

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

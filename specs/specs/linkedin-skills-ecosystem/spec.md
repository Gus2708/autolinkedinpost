# Spec: linkedin-skills-ecosystem

## Domain Overview
Domain behavior synchronized from change artifacts.

## Requirements

### Requirement: linkedin-skills-ecosystem/skills-discovery — Registration of 11 LinkedIn Skills
The system MUST provide 11 standalone, modular LinkedIn agent skills under \.agents/skills/\ with valid YAML frontmatter specifying name and actionable description.

#### Scenario: Agent discovers LinkedIn skills
- GIVEN an agent scanning available workspace skills in \.agents/skills/\
- WHEN the agent lists skills matching LinkedIn content operations
- THEN each of the 11 skills (\linkedin-post-writer\, \linkedin-comment-drafter\, \linkedin-reply-handler\, \linkedin-humanizer\, \linkedin-hook-extractor\, \linkedin-content-planner\, \linkedin-thread-monitor\, \linkedin-engager-analytics\, \linkedin-profile-optimizer\, \linkedin-employee-advocacy\, \linkedin-repurposer\) is discoverable and executable.

### Requirement: linkedin-skills-ecosystem/reference-guides — Centralized Reference Knowledge Base
The system MUST provide 8 authoritative LinkedIn reference guides under \docs/references/\ and \.agents/skills/references/\.

#### Scenario: Skill accesses algorithmic and voice reference guides
- GIVEN a skill or developer requiring LinkedIn hook formulas or algorithmic rules
- WHEN the file system is inspected at \docs/references/\
- THEN the 8 reference documents (\hook-formulas.md\, \lgorithm-heuristics.md\, \
oice-rules.md\, \
ounder-topics.md\, \engagement-metrics-taxonomy.md\, \industry-benchmarks.md\, \untrusted-content.md\, \
oice-profile.md\) are present with full text intact.

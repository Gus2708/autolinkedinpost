# Delta Spec: anti-ai-quality-gates

## ADDED Requirements

### Requirement: anti-ai-quality-gates/no-ai-slop-patterns — Extended AI Slop Pattern Detection
The system MUST detect and report the extended AI slop patterns from no-ai-slop in both Spanish and English:
1. Faux-insight setups ("What most people get wrong", "The part everyone misses", "Lo que nadie te cuenta", "La parte que todos ignoran").
2. Colon reveals (dramatic reveals after noun phrases: "The detail that makes it work: ...", "El secreto: ...").
3. Superficial analysis with trailing gerunds ("highlighting", "underscoring", "reflecting", "showcasing", "destacando", "subrayando", "demostrando").
4. Importance puffery ("stands as a testament", "marks a pivotal moment", "plays a vital role", "un testimonio de", "marca un hito").
5. Interpretive metadiscourse ("That last part matters more than it sounds", "The key point is", "Esa última parte importa más de lo que parece").
6. Weasel attribution ("Experts agree", "industry reports suggest", "estudios demuestran", "muchos argumentan").
7. Rhetorical setups ("What if I told you", "Think about it:", "¿Qué pasaría si te dijera...").
8. Fake-profound kickers and summary-recap endings ("In conclusion", "Ultimately", "En conclusión", "En última instancia").

#### Scenario: Detect faux-insight and colon reveals
- GIVEN a draft text containing "Here's what nobody tells you: distribution is the moat"
- WHEN `audit_text_humanizer_qc` is executed
- THEN it reports violations for faux-insight setup and colon reveal with concrete replacement suggestions.

#### Scenario: Detect superficial analysis with trailing gerunds
- GIVEN a draft text containing "The release includes Redis caching, highlighting our commitment to speed"
- WHEN `audit_text_humanizer_qc` is executed
- THEN it reports a violation for superficial trailing gerund analysis.

### Requirement: anti-ai-quality-gates/banned-vocabulary — Banned Words and Empty Fillers
The system MUST detect and flag outright banned buzzwords and empty filler phrases cataloged in no-ai-slop:
- Banned outright: delve, foster, leverage, utilize, facilitate, empower, streamline, robust, cutting-edge, paradigm shift, game changer, tapestry, realm, beacon, multifaceted, meticulous, intricate, paramount, transformative, elevate, embark, supercharge, harness, ever-evolving (and their Spanish counterparts: profundizar, fomentar, apalancar, utilizar, facilitar, empoderar, optimizar/agilizar cliché, robusto, vanguardista, cambio de paradigma, tapiz, reino, multifacético, meticuloso, intrincado, primordial, transformador, embarcar, potenciar cliché).
- Empty filler phrases: "at the end of the day", "in today's world", "the reality is", "al fin y al cabo", "en el mundo actual", "la realidad es".

#### Scenario: Detect banned buzzword in English text
- GIVEN a draft text containing "We leverage cutting-edge tech to supercharge workflows"
- WHEN `audit_text_humanizer_qc` is executed with `language="en"`
- THEN it detects "leverage", "cutting-edge", and "supercharge" as slop violations.

#### Scenario: Detect banned buzzword in Spanish text
- GIVEN a draft text containing "Decidí apalancar una arquitectura vanguardista para potenciar el pipeline"
- WHEN `audit_text_humanizer_qc` is executed with `language="es"`
- THEN it detects "apalancar", "vanguardista", and "potenciar" as slop violations.

### Requirement: anti-ai-quality-gates/sanitizer-expansion — Deterministic Slop Sanitization
The system MUST deterministically strip or replace obvious slop phrases, greetings, and banned vocabulary during preprocessing without corrupting technical syntax or identifiers.

#### Scenario: Clean banned vocabulary deterministically
- GIVEN a raw post containing "utilize Redis" and "in order to streamline"
- WHEN `sanitize_text_humanizer` is executed
- THEN "utilize" is replaced with "use" and "in order to streamline" is simplified to direct verbs.

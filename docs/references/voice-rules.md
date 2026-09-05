# Voice Rules for Comments

## Hard rules

1. **No em dashes** (`—`), en dashes (`–`), or double dashes (`--`). Biggest AI tell.
2. **Use `..` as soft pause** when you'd reach for an em dash. Feels human, matches the author's own rhythm.
3. **Capitalize personal names, company names, product names** (HubSpot, Claude, etc.). Lowercase reads as disrespectful.
4. **Sentence starts can be lowercase** (natural voice), but names inside are always capitalized.
5. **Don't mention the user's own product by name** in comments on third-party posts. Describe what they do instead ("our AI content system", "the platform we're building").

## Vocabulary blacklist (petergyang/no-ai-slop)

Never use in posts or comments:
- leverage, utilize, facilitate, streamline, robust, seamless, delve, navigate, unlock, harness, foster, cultivate, supercharge, cutting-edge, paradigm shift, transformative, elevate, embark, ever-evolving, tapestry, realm, beacon, multifaceted, meticulous, intricate, paramount
- fundamentally, essentially, ultimately, crucially, notably, actually, truly, inherently, inevitably
- landscape, ecosystem, paradigm, realm, tapestry, journey
- "It's not just X, it's Y" / "It's not X. It's Y."
- "In today's fast-paced world" / "In today's digital landscape" / "At the end of the day" / "The reality is"
- "Game-changer", "deep dive", "stands as a testament to", "pivotal moment", "vital role"

## No-AI-Slop Structural Anti-patterns (20+ Patterns)

1. **Binary contrasts**: "This is not X. It's Y." / "The question isn't X, it's Y." -> State Y directly.
2. **Throat-clearing openers**: "Here's the thing", "Let me be clear", "The uncomfortable truth is" -> Cut and start with the raw engineering challenge.
3. **Faux-insight setups**: "What most people get wrong", "The part everyone misses", "Here's what nobody tells you" -> Cut setup; let the technical claim stand on its own.
4. **Colon reveals**: Noun phrase, colon, lowercase reveal ("The secret: it runs on SQLite") -> Use complete sentences. Colons are for lists, code, and quotes.
5. **Superficial analysis (-ing clauses)**: Trailing ", highlighting...", ", underscoring...", ", reflecting..." -> State direct causal mechanism or consequence.
6. **Importance puffery**: "Stands as a testament", "marks a pivotal moment", "plays a vital role" -> State concrete technical facts.
7. **Interpretive metadiscourse**: "That last part matters more than it sounds", "The key point is" -> Delete author commentary; facts carry weight.
8. **Weasel attribution**: "Experts agree", "studies show", "industry reports suggest" -> Name specific source/benchmark or describe mechanism.
9. **Fake-strong verbs**: Avoid pompous verbosity ("serves as a centralized hub" -> "tracks X in one place").
10. **Synonym cycling**: If the right term is Redis, keep using Redis; don't cycle synonyms for faux variety.
11. **Negative listing**: "Not an X. Not a Y. A Z." -> Just say Z.
12. **Dramatic fragmentation**: "X. And Y. And Z." -> Use complete sentences.
13. **Robotic rhythm**: Avoid identical paragraph shapes and stacked punchy fragments.
14. **Rhetorical setups**: "What if I told you...", "Think about it:", "Plot twist:" -> State the fact.
15. **Fake-profound kickers**: Cut cute aphorisms or mic-drop metaphors at the end. End on a concrete takeaway or architecture trade-off.
16. **Summary-recap endings**: Cut "In conclusion", "Ultimately", "Overall".
17. **Formatting slop**: No decorative bold sprinkled mid-sentence, no emojis in headers.
18. **Em dashes**: Zero in short copy; maximum 1-2 in longer drafts if they beat commas or parentheses.
19. **Portability test**: If a sentence could be lifted into another company or stack without changes, cut or ground it in specific numbers, dates, and code.
20. **Minimum effective edit**: Preserve author cadence, bluntness, and genuine engineering edge.

## Structure

- 200-350 chars. Two short paragraphs max. Line break between them.
- One concrete number or named entity per comment minimum.
- One line that could be screenshot and quoted standalone.
- Never end with "What do you think?" — dead prompt. End with a specific question or a clean landing.

## Anti-patterns

- Thesis restatement ("so true, AI is changing everything")
- Generic praise ("great insight!", "love this")
- Overused openers: "This.", "100%", "Couldn't agree more"
- Rule of three ("faster, cheaper, better")
- Passive voice over 10% of clauses

## Algorithmic Scoring Criteria (NLP-level)

LinkedIn's ranker runs NLP on comments and rewards:

- **Depth** — comments with ≥12 words and multiple sentence structures
- **New keywords** — introduce at least one noun/concept NOT already in the parent post
- **Questions** — end with one that invites a sub-thread
- **Sub-thread sparks** — comments that generate replies from the author AND other commenters count as a strong signal

**Before submitting, check:** does your comment add at least one noun/concept not already in the post? If no, rewrite.

# Intent: carousel-design-rotation-fix

## Context
Users report that carousel PDFs consistently use the same design system across generations because design rotation offsets are held only in ephemeral process memory (USER_ROTATION_CACHE) which resets to 0 on every server restart, dyno sleep, or standalone CLI run. Additionally, tests and ad-hoc scripts often default or fix theme_id='swiss', preventing visual diversity across generated content.

## Desired Outcome
Every newly generated carousel PDF automatically cycles through all 6 Refero design systems (Editorial, Terminal, Swiss Grid, Blueprint, Monograph, Linear) sequentially, backed by persistent rotation state in data/carousel_rotation.json that survives bot restarts, container redeployments, and script invocations.

## Scope
### In Scope
- Create persistent rotation manager src/carousel_rotation.py with get_next_rotating_theme and state persistence.
- Integrate persistent rotation into bot.py so Telegram showcase generation advances themes sequentially across restarts.
- Integrate persistent rotation into src/carousel_renderer.py and main.py when theme_id is omitted.
- Update Telegram bot notification copy to display the active theme name and icon.
- Add comprehensive automated test suite covering persistence, crash resilience, multi-chat isolation, and cycling through all 6 systems without duplicates.

### Out of Scope
- Creating new design systems beyond the 6 canonical ones.
- Modifying CSS styles of existing design systems.

## Key Decisions
- Decision: Use a lightweight JSON file data/carousel_rotation.json for persistence with atomic write semantics to survive server restarts.
- Decision: Fall back gracefully to deterministic day/hash rotation if disk write fails or is read-only.
- Decision: Allow explicit theme_id override in CLI or bot commands to bypass rotation when a user specifically wants a particular theme.

## Success Criteria
- [ ] Rotating theme advances sequentially across 6 systems without repeats in consecutive single-project runs.
- [ ] Rotation state persists across process restarts (reading from disk cache).
- [ ] Bot showcase generation increments persistent rotation counter and reports active theme in Telegram message.
- [ ] 100% of existing tests continue to pass with new regression tests added.

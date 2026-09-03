# Tasks: carousel-design-rotation-fix

## Review Workload Forecast
Estimated changed lines: 120-200
Estimated product files: 3-4
Target budget: 800 lines, 15 files
Hard limit: 1000 lines, 25 files
Budget risk: Low
Independent slices possible: No
Shared production files across slices: No
Forecast basis: brief flow proposal and inspection of carousel_renderer.py, bot.py, design_systems.py

## Delivery Plan
Strategy: single-pr
Model: whole
PR mode: draft
PR creation point: final verify only
Current delivery unit: whole

### Whole Delivery
Planned branch/base: sdd/carousel-design-rotation-fix -> main
Scope: Implement persistent design rotation across carousel generations, integrate with bot and renderer, and add regression tests.

## Slice: whole — Carousel Design Rotation Fix

### Phase 1: Persistent Rotation Manager
- [x] 1.1 Implement persistent carousel rotation manager in src/carousel_rotation.py
  - [x] 1.1.a Safety Net evidence: verify existing design system catalog in tests/test_carousel.py
  - [x] 1.1.b RED failing test: assert rotation persists and advances across process restarts in tests/test_carousel_rotation.py
  - [x] 1.1.c GREEN implementation: implement CarouselRotationManager in src/carousel_rotation.py
  - [x] 1.1.d TRIANGULATE second case: assert wrap-around after 6 systems and multi-chat/project key isolation
  - [x] 1.1.e REFACTOR evidence: clean atomic write semantics and error recovery

### Phase 2: Integration with Renderer and Bot
- [x] 2.1 Integrate persistent rotation into src/carousel_renderer.py and bot.py
  - [x] 2.1.a Safety Net evidence: verify generate_native_carousel_pdf without theme_id in tests/test_carousel.py
  - [x] 2.1.b RED failing test: assert bot and renderer advance persistent themes across consecutive runs
  - [x] 2.1.c GREEN implementation: wire CarouselRotationManager into carousel_renderer.py and bot.py
  - [x] 2.1.d TRIANGULATE second case: assert explicit theme_id overrides persistent rotation without advancing counter
  - [x] 2.1.e REFACTOR evidence: clean fallback to default deterministic hash when disk is unavailable

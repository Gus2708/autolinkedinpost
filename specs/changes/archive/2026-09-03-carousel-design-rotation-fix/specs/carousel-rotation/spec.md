# Delta Spec: carousel-rotation

## ADDED Requirements

### Requirement: carousel-rotation/persistent-theme-cycling — Persistent Theme Rotation
The system MUST persist the design system rotation index across process runs and advance to the next distinct design system on each carousel generation when no explicit theme is requested.

#### Scenario: Consecutive Generations Cycle Systems
- GIVEN an active carousel rotation manager with 6 design systems
- WHEN consecutive carousel generations occur for the same project or user
- THEN each generation receives a distinct design system in sequence (Editorial -> Terminal -> Swiss Grid -> Blueprint -> Monograph -> Linear) wrapping after 6.

#### Scenario: Persistence Across Process Restarts
- GIVEN a rotation index previously advanced to offset N and saved to disk
- WHEN a new process instance initializes without in-memory state
- THEN the rotation manager reads offset N from disk and assigns offset N+1 to the next generation.

### Requirement: carousel-rotation/explicit-override — Explicit Theme Selection Bypass
The system MUST bypass persistent rotation when an explicit theme_id is supplied by the user or caller.

#### Scenario: User Specifies Explicit Theme
- GIVEN a request specifying theme_id='terminal'
- WHEN generate_native_carousel_pdf is invoked
- THEN the carousel is rendered using 'terminal' without advancing the persistent rotation index.

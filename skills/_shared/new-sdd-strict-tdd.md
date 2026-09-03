# New SDD Strict TDD Contract

## Purpose

TDD is the implementation discipline for every new SDD flow. Tests drive behavior and design; they are not an afterthought.

## Three Laws

1. Do not write production code until a failing test exists.
2. Do not write more test than needed to fail meaningfully.
3. Do not write more production code than needed to pass.

## Cycle Per Task

```text
1. SAFETY NET
   Run the existing test file/class nearest to the changed symbol plus every safety-net command named by the task/design.
   If neither exists, record `No pre-existing coverage`.
   If they fail, stop and report pre-existing failure.

2. UNDERSTAND
   Read task, spec scenario, design constraints, and existing code patterns.

3. RED
   Write a failing test for the expected behavior.
   The test must exercise production behavior, not a tautology.

4. GREEN
   Write the smallest production code needed to pass.
   Run the targeted test and capture output.

5. TRIANGULATE
   Add a meaningfully different case unless the task is purely structural.
   Generalize fake/hardcoded code when the second case requires it.

6. REFACTOR
   Improve naming, duplication, seams, or clarity while tests remain green.

7. MARK COMPLETE
   Update tasks artifact with `[x]` only after evidence exists.
```

## Test Layer Selection

| Behavior | Preferred Layer |
|---|---|
| pure logic, calculation, parser, transformation | unit |
| component interaction, provider/context, API boundary | integration |
| critical user journey, cross-page flow | e2e |

If the ideal layer is unavailable, degrade to the next available layer and record the reason.

## Approval Tests For Refactor

For refactoring existing behavior:

1. Capture current behavior with approval tests.
2. Run approval tests and confirm they pass.
3. Refactor.
4. Run approval tests again.
5. If the spec changes behavior, update/add a RED test for the new behavior before changing production code.

## Refactor-Only Evidence Matrix

Refactor tasks still use exactly five ordered subtasks: Safety Net, RED, GREEN,
TRIANGULATE, and REFACTOR. The main task remains pending until the user accepts
the revision. Record real evidence for every executed subtask; only these
specific exemptions are allowed:

| Subtask | Required work | `N/A — reason` allowed |
|---|---|---|
| Safety Net | Run relevant existing coverage. | No useful coverage exists or validation belongs only to the user. |
| RED | Add or use a failing behavioral test first. | Visual, documentary, or structural work without automatable behavior. |
| GREEN | Make the minimum requested change. | Never. |
| TRIANGULATE | Add a meaningfully different case when it prevents overfitting. | Punctual or structural work with no meaningful second case. |
| REFACTOR | Improve structure, naming, or duplication when needed. | The minimum change is already clean. |

Generic `N/A` is never evidence. Ordinary non-refactor tasks retain the normal
strict-TDD rules above; these proportional exemptions must not leak into them.

## Banned Assertions

Do not write:

```text
expect(true).toBe(true)
assert True
expect(result).toBeDefined()  # by itself
expect(items).toEqual([])     # unless setup proves why empty is meaningful
assertions inside loops that may execute zero times
snapshot-only tests for behavioral requirements
```

Every assertion must prove behavior that a bug could break.

## Task-Owned Evidence

For new hierarchical plans, record each cycle directly in the parent task's
`N.M.a`–`N.M.e` subtasks and mark the parent only after all five roles have
evidence. `tasks.md` is the only implementation-progress record; do not create
parallel apply-progress evidence. A structural task keeps `N.M.d` and records
the reason triangulation is not applicable.

## Evidence Table (legacy compatibility)

```markdown
### TDD Cycle Evidence
| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
```

Missing RED or missing GREEN evidence is a failed TDD cycle. The table remains
valid only for explicitly recognized legacy apply-progress artifacts; new
verification derives TDD compliance from task-owned subtasks, the diff,
executed tests, and asserted outcomes.

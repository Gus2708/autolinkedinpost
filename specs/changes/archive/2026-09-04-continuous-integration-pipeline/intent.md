# Intent: continuous-integration-pipeline

## Context
The repository currently relies on a minimal single-version test workflow (	ests.yml) that runs only on Python 3.11 without matrix testing, syntax compilation checks, concurrency cancellation, or automated code quality checks (linting/formatting). As the codebase expanded with multi-backend publishing, PDF rendering, Telegram approval loops, and persistent rotation, PRs and commits require a robust, fast, and multi-version Continuous Integration (CI) pipeline that guarantees stability and eliminates regressions before reaching main or production.

## Desired Outcome
A comprehensive Continuous Integration (CI) GitHub Actions pipeline (.github/workflows/ci.yml) that validates Python syntax, runs multi-version matrix testing (Python 3.11 & 3.12), enforces code quality and linting via Ruff, executes the full automated test suite with concurrency cancellation for pending commits, and displays CI build badges in README.md.

## Scope
### In Scope
- Create .github/workflows/ci.yml with concurrency control, Python matrix testing (3.11, 3.12), syntax compilation check (compileall), linting, and full test execution.
- Add 
uff and test dependencies to 
equirements-dev.txt.
- Add CI status badge to README.md.
- Ensure backwards compatibility with existing GitHub Actions workflows (daily_linkedin_post.yml).
- Add tests validating workflow syntax and CI configuration.

### Out of Scope
- Deploying to production hosting environments (handled by Render CD and daily cron).
- Modifying core application business logic.

## Key Decisions
- Decision: Use Ruff for linting in CI because it executes in milliseconds without slowing down CI feedback loops.
- Decision: Use GitHub Actions concurrency group with cancel-in-progress: true to save runner minutes when commits are pushed rapidly.
- Decision: Test across Python 3.11 and 3.12 matrix on ubuntu-latest.
- Decision: Replace/upgrade the basic 	ests.yml with the unified ci.yml workflow.

## Success Criteria
- [ ] .github/workflows/ci.yml is valid YAML and passes GitHub Actions schema checks.
- [ ] CI pipeline includes Python matrix testing (3.11 & 3.12) with concurrency cancellation.
- [ ] 
equirements-dev.txt specifies linting and development tools.
- [ ] 100% of existing tests pass locally and in the new CI matrix.
- [ ] CI status badge is visible in README.md.

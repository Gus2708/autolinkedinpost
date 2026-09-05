# Agent Guidelines & Project Rules

## Open-Source Compliance & Zero Hardcoding (Strict Rule)

1. **No Personal or Private Hardcoding**:
   - NEVER hardcode personal usernames, handles, author names, email addresses, or specific repository names (e.g. user accounts or private projects) in tests, product code, templates, scripts, or examples.
   - This project is open-source. All tests and examples must run identically for any user or contributor without requiring changes to the source code.

2. **Dynamic Environment Configuration**:
   - Always read repository names, author handles, and credentials from environment variables:
     * `TEST_REPO_NAME` or `GITHUB_REPOSITORY` for repository targets.
     * `GITHUB_ACTOR`, `GITHUB_USER`, or `GH_USERNAME` for author usernames.
     * `GH_AUTHOR_NAME` and `GH_AUTHOR_EMAILS` for commit identity matching.
   - Always provide neutral, generic fallback values when environment variables are not defined:
     * Repositories: `"example-org/sample-repo"` or `"project"`.
     * Users/Authors: `"sample-user"`, `"author"`, or `"github"`.

3. **Conventional Commits & Attribution**:
   - Use conventional commit format only (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, etc.).
   - NEVER add `Co-Authored-By` or AI attribution tags to commit messages.

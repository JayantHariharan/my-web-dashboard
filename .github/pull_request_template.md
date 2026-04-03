# Pull Request Checklist

Thank you for contributing to PlayNexus! Before submitting this PR, please complete the following:

## Pre-requisites
- [ ] I have read the [CONTRIBUTING.md](./CONTRIBUTING.md) and [DEVELOPER.md](./docs/DEVELOPER.md)
- [ ] My code follows the project's code style and conventions
- [ ] I have run `./scripts/run-quality-checks.sh` locally and all checks pass
- [ ] My changes generate no new warnings or errors

## Database Changes
- [ ] If I added/modified a database migration:
  - [ ] Migration file is in `flyway/sql/` with proper naming `V<number>__<description>.sql`
  - [ ] Used `{AUTOINCREMENT}` for auto-incrementing primary keys
  - [ ] Used `{TEXT}` for text fields (database-agnostic)
  - [ ] Added `IF NOT EXISTS` for tables and indexes where appropriate
  - [ ] Migration is idempotent (can be safely re-run)
  - [ ] Tested migration locally with `python scripts/migrate.py`

## Security Review
- [ ] No hardcoded secrets or credentials (use environment variables)
- [ ] All SQL queries use parameterized queries (repository pattern)
- [ ] Passwords are hashed with bcrypt + pepper
- [ ] Rate limiting is enabled on sensitive endpoints
- [ ] No sensitive data is logged
- [ ] Input validation is performed on all user inputs
- [ ] Authentication/authorization checks are in place for new endpoints

## Testing
- [ ] Added or updated tests for new functionality
- [ ] Existing tests pass locally (if applicable)
- [ ] Smoke test passes: `SITE_URL=<url> node tests/smoke.test.js`
- [ ] Manual testing completed and documented below

## Documentation
- [ ] Updated API documentation in `docs/API-REFERENCE.html` (if API changes)
- [ ] Updated user documentation (if user-facing changes)
- [ ] Updated `README.md` with new features or setup changes
- [ ] Added or updated code comments where necessary
- [ ] Updated architecture diagrams if needed

## Frontend Changes (if applicable)
- [ ] UI changes are responsive and work on mobile
- [ ] Accessibility considerations addressed (ARIA labels, keyboard navigation)
- [ ] Cross-browser compatibility tested (Chrome, Firefox, Safari)

## Backend Changes (if applicable)
- [ ] New endpoints follow RESTful conventions
- [ ] Proper HTTP status codes are used
- [ ] Error messages are informative but don't leak sensitive info
- [ ] Rate limiting is configured appropriately
- [ ] Logging is added for important operations

## Performance Considerations
- [ ] No N+1 query issues introduced
- [ ] Database queries are optimized with proper indexing
- [ ] Static assets are cached appropriately
- [ ] Gzip compression enabled for responses

## Git Hygiene
- [ ] Commits are logically grouped and follow [Conventional Commits](https://www.conventionalcommits.org/)
- [ ] No merge commits in PR history (squash merge recommended)
- [ ] No temporary/debug code or console.log statements
- [ ] No sensitive data in commit history

## Deployment Readiness
- [ ] CI/CD pipeline passes (GitHub Actions)
- [ ] All required secrets are available in GitHub repository settings
- [ ] No environment-specific hardcoded values
- [ ] Rollback plan considered (if this is a risky change)

---

## Testing Performed

<!-- Describe the testing you performed, including any manual testing, automated tests, and edge cases. This helps reviewers understand your QA process. -->

## Additional Notes

<!-- Any other information that reviewers should know: architectural decisions, trade-offs, open questions, etc. -->

## Screenshots / Demo

<!-- If this is a UI change, please include screenshots or a short video/GIF demonstrating the new functionality. Use: -->

---

**Reviewer Checklist:**
- [ ] All checklist items addressed
- [ ] Code reviewed for security vulnerabilities
- [ ] Architecture/design evaluated
- [ ] Tests are adequate
- [ ] Documentation complete
- [ ] Ready to merge ✅

---

*By submitting this PR, I acknowledge that I have read the Code of Conduct and agree to abide by its terms.*

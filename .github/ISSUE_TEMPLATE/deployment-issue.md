---
name: 🚀 Deployment Issue
about: Report problems with CI/CD, Render, or GitHub Actions
title: "[DEPLOY] "
labels: deployment, ci-cd
assignees: ''
---

## 🚀 Deployment Issue Description

A clear and concise description of the deployment problem.

## Affected Environment

- [ ] Staging (`playnexus-test.onrender.com`)
- [ ] Production (`playnexus-prod.onrender.com`)
- [ ] GitHub Actions workflow (CI/CD)

## Deployment Details

- **Branch/tag being deployed**: [e.g., `main`, `develop`, `v1.2.0`]
- **When did the issue start?**: [e.g., "After commit abc123 on 2026-04-03"]
- **Workflow run URL** (if applicable): [link to GitHub Actions run]

## Error Messages / Logs

**GitHub Actions logs:**
```yaml
[Paste relevant error logs from the workflow run]
```

**Render logs:**
[Access Render dashboard → Service → Logs and paste relevant entries]

**Application logs:**
```log
[Paste any application-level error messages]
```

## Steps Already Tried

Describe what you've already attempted to fix the issue:
1. [x] Restarted Render service
2. [ ] Rolled back to previous deployment
3. [ ] Checked database connectivity
4. [ ] Verified environment secrets
5. [ ] Other: ______

## Related Checks

- [ ] All GitHub Actions secrets are properly configured (see `SECRETS.md`)
- [ ] Database migrations are up-to-date (`flyway/sql/`)
- [ ] Render service environment variables are correct
- [ ] No recent changes to infrastructure (SQL schema, Render settings)

## Additional Context

Add any other information that might help diagnose the issue:
- Changes made before the deployment failure
- Network/firewall issues
- Third-party service outages (e.g., Supabase status)
- Recent dependency updates

## Checklist

- [ ] I have included relevant logs and error messages
- [ ] I have checked existing issues for duplicates
- [ ] I have verified secret configuration (not posting secrets, just confirming they exist)

---

**Note**: For urgent production issues, alert the on-call engineer immediately after creating this issue.

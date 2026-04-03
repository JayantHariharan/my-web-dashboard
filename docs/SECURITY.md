# Security Policy

**PlayNexus** takes security seriously. This document describes our security practices and how to report vulnerabilities.

## 🔒 Security Features

### Automated GitHub Security Scanning

We use GitHub's native security infrastructure:

- **CodeQL** – Static analysis scans Python and JavaScript code on every PR/push
  - Detects: SQL injection, XSS, CSRF, path traversal, hardcoded secrets, and OWASP Top 10
  - Results: Visible in GitHub Security tab, PR annotations, and block merges on high-severity findings
  - Configuration: `.github/workflows/codeql-analysis.yml`

- **Dependabot** – Automatic dependency updates
  - Scans `requirements.txt` and GitHub Actions weekly
  - Opens PRs for outdated or vulnerable dependencies
  - Configuration: `.github/dependabot.yml`

- **Secret Scanning** – Detects accidentally committed secrets
  - Enabled on all pushes (GitHub's built-in feature)
  - Alerts appear in repository **Security** tab
  - Push protection blocks secrets before they're committed (if enabled)

### Branch Protection

Both `main` (production) and `develop` (staging) branches have protection rules:
- Required status checks: CodeQL scan, quality checks must pass
- Minimum 1 reviewer approval
- Linear history (squash merging)
- No force pushes

## 🛡️ Application Security

### Authentication
- bcrypt password hashing with pepper
- Rate limiting on auth endpoints (20 requests/hour per IP)
- Session-based authentication (no JWT stored in localStorage)

### Database
- Parameterized queries via repository pattern (prevents SQL injection)
- Environment-specific table suffixes (`_prod`, `_test`)
- Migrations versioned with Flyway-style SQL scripts

### Infrastructure
- Render hosting with automatic HTTPS
- Environment variables for secrets (no hardcoded credentials)
- Database credentials scoped per environment

### CI/CD
- Secrets stored in GitHub Actions (encrypted)
- Automated smoke tests after deployment
- Health checks before marking deployment successful

## 🐛 Reporting a Vulnerability

**Please do NOT open a public issue for security vulnerabilities.** Use private reporting instead.

### Option 1: GitHub Security Advisory (Recommended)
1. Go to **Security** tab → **Advisories** → **New draft security advisory**
2. Describe the vulnerability with reproduction steps
3. Choose "This repository only" for initial private coordination
4. Our team will respond within 72 hours

### Option 2: Security Issue Template
Use `.github/ISSUE_TEMPLATE/security-vulnerability.md` (mark as confidential).

### Option 3: Direct Email (if available)
[Add your security contact email here]

## 🔐 What to Include in Your Report

- **Type of vulnerability** (e.g., SQL injection, XSS, authentication bypass, information disclosure)
- **Affected component** (endpoint, file, or module)
- **Steps to reproduce** (clear, sanitized – do NOT include real credentials or exploit details publicly)
- **Potential impact** (data exposure, unauthorized access, DoS, etc.)
- **Your suggestion for remediation** (if any)

## 📋 Security Checklist for Contributors

Before submitting a PR:
- [ ] No hardcoded secrets or API keys
- [ ] All SQL uses parameterized queries
- [ ] Passwords hashed with bcrypt (use `security.py` utilities)
- [ ] Rate limiting considered for new endpoints
- [ ] Sensitive data not logged
- [ ] Input validation on all user inputs
- [ ] Authentication/authorization enforced

## 🔍 Ongoing Security Maintenance

- **Dependencies**: Dependabot will automatically open PRs for outdated packages. Review and merge promptly.
- **Secrets rotation**: Rotate Render API keys and database passwords periodically (recommended: quarterly)
- **Access review**: Audit GitHub repository collaborators and Render service access regularly
- **Logs monitoring**: Review Render logs for suspicious activity

## 📞 Contact

For urgent security issues, contact the maintainer directly via GitHub or email.

---

**Last Updated**: 2026-04-03

## 📚 External Resources

- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [GitHub Security Lab](https://securitylab.github.com/)
- [FastAPI Security](https://fastapi.tiangolo.com/advanced/security/)
- [Render Security Best Practices](https://render.com/docs/security)

# Security Policy

## Reporting a Vulnerability

The Prospect AI team takes security vulnerabilities seriously. If you discover a security vulnerability in Prospect AI, please report it to us responsibly.

### How to Report

**Do not** file a public GitHub issue for security vulnerabilities. Instead, please email your report to **security@craftedwithintent.com** with the following information:

1. **Type of vulnerability** — (e.g., cache poisoning, injection, authentication bypass)
2. **Location** — Specific file(s), module(s), or API endpoint(s) affected
3. **Description** — Clear explanation of the vulnerability and its impact
4. **Proof of Concept** — Minimal reproducible example
5. **Suggested Fix** — If you have one (optional)

### Response Timeline

- **Acknowledgment** — Within 24 hours
- **Initial assessment** — Within 48 hours
- **Patch or mitigation** — Within 7-14 days (depending on severity)
- **Public disclosure** — After patch is released

### Supported Versions

| Version | Status | Security Updates |
|---------|--------|------------------|
| 1.0.x   | Beta   | Yes (active development) |
| < 1.0.0 | EOL    | No |

### Security Best Practices

When using Prospect AI in production:

1. **API Keys** — Never commit upstream API keys to git. Use environment variables.
2. **Cache Storage** — Ensure access control:
   - SQLite: Restrict file permissions (mode 0600)
   - Redis: Enable AUTH and restrict network access
3. **Sensitive Data** — Avoid caching responses containing PII/credentials.
4. **Dependencies** — Regularly run `pip install --upgrade prospect-ai`
5. **CI/CD Integration** — Use GitHub Secrets for API keys (never commit to public repos)
6. **Network Security** — Use TLS/HTTPS in production (reverse proxy recommended)

### Scope

Prospect AI is designed for LLM inference optimization in controlled environments. It is **not** intended for:

- Handling sensitive user data directly (PII, credentials)
- Serving as a security scanning tool
- Operating as a public-facing API without additional authentication

---

**Questions?** Contact us at **team@craftedwithintent.com**.

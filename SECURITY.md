# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in TradeCRM, please report it responsibly. Do not open a public GitHub issue for security vulnerabilities.

### Contact

Send vulnerability reports to: **security@tradecrm.dev**

Include the following information:

- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

### Response Timeline

- **Acknowledgment**: Within 48 hours of receiving the report
- **Initial assessment**: Within 5 business days
- **Fix timeline**: Depends on severity; critical issues targeted for resolution within 7 days

### What Happens Next

1. We will confirm receipt of your report
2. We will investigate and validate the vulnerability
3. We will develop and test a fix
4. We will release a patch and credit you in the changelog (unless you prefer to remain anonymous)

---

## Scope

The following areas are in scope for security reports:

- Authentication and authorization bypass
- SQL injection, XSS, or CSRF vulnerabilities
- Tenant isolation failures (cross-tenant data access)
- API key or credential exposure
- Insecure handling of OAuth tokens
- Privilege escalation between user roles
- Webhook signature verification bypass

The following are out of scope:

- Vulnerabilities in third-party services (Clerk, SendGrid, GupShup, etc.) -- report those to the respective vendors
- Denial of service attacks
- Social engineering
- Issues requiring physical access

---

## Security Best Practices for Deployers

- Store all API keys and secrets as environment variables
- Enable HTTPS for all public endpoints
- Set `DEV_MODE=false` in production
- Use managed database services with SSL enabled
- Rotate the `ENCRYPTION_KEY` periodically
- Review Clerk webhook signatures
- Restrict CORS to your frontend domain only

---

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x | Yes |

We only provide security patches for the latest release.

# ADR 0004 — No authentication in v1 (single-user local pilot)

**Status:** Accepted (2026-04-29) · Hard-block for any client demo or external exposure.
**Deciders:** Saurabh Jalendra

## Context

Quant Agent is being developed solo, on a single machine, by a single user (the author). Every endpoint under `/api/*` is currently open: any actor with network access to port 8000 can POST chat messages, read any audit log, list every session, and export every PDF.

## Decision

**No authentication layer in v1.** The product is built and operated as a single-user local development tool. CORS is locked to the developer's local frontend (`localhost:3000` / `:5173`) via an env-driven allowlist. Rate-limiting is per-IP (slowapi) as a denial-of-service guard, not a credential check.

## Consequences

**Positive**
- Zero auth surface to design, test, or maintain during v1.
- Friction-free local development.
- Decision is reversible — auth can be added as middleware without changing endpoint signatures.

**Negative**
- **Cannot be exposed to the internet.** Any production deploy must terminate behind an authenticating proxy (e.g., a corporate SSO gateway).
- **Cannot be demoed to a real client.** The compliance posture in the UI (entitlements pill, MNPI walls indicator) is purely cosmetic.
- The audit log is mutable and identity-less. Any audit trail captured is non-attestable.
- The frontend BrandBar / ComplianceBar UI elements that imply authenticated identity are intentionally hardcoded placeholders during v1.

## Alternatives considered

1. **Session token (HS256 JWT, no rotation).** Adds ~2 days of work; minimal value while there is only one user.
2. **OIDC (Okta / Auth0 / Azure AD).** Right answer for a client deploy. Out of scope for the local pilot.
3. **SAML 2.0.** Required for enterprise IB clients. Future ADR.

## Reversal criteria

Add auth (and write an ADR superseding this one) BEFORE:
- Any deployment outside the author's laptop.
- Any demo to a third party where the URL might be observed.
- Any commit to `main` that includes a real-world client identifier or MNPI sample.

Minimum viable auth when reversed:
- Session token (HS256 JWT) issued by a `/api/auth/login` endpoint; backed by a flat YAML user list for the first client.
- Token in `Authorization: Bearer …` on every API call and in the SSE URL via `?token=...`.
- BrandBar / ComplianceBar read identity from the token claims.
- Audit log entries carry the authenticated subject.

## References

- Threat model: see audit `docs/audit/2026-05-20-deep-audit.md` finding C2 (compliance bar cosmetic).
- Implementation gap: `backend/app/main.py` (no auth dependency injected into any handler).
- Audit log identity gap: `backend/app/audit_logger.py` (no `actor` column on `audit_log`).

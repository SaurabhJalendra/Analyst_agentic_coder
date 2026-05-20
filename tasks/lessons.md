# Lessons

> Self-improvement log. After any user correction or notable finding, append one entry. Review at session start. Pull patterns into rules, not just war stories.

<!-- Format:
## YYYY-MM-DD
- **Mistake / pattern**: brief description
- **Rule**: what to do differently next time
- **Where it applied**: file / area / command
-->

## 2026-05-20

- **Audit agents can produce false positives**: today's 7-agent audit incorrectly flagged `.env` as committed (it isn't), claimed a double-DoneEvent race (the logic correctly gates it via `emitted_done`), said the hardcoded CLI path was still present (it was fixed in commit `909c62b`), and called the placeholder BrandBar removal a UX bug (it was intentional cleanup).
- **Rule**: verify every agent finding against actual code before propagating. Cite `file:line`. The audit document explicitly lists false positives so the user doesn't chase ghosts.
- **Where it applied**: `docs/audit/2026-05-20-deep-audit.md` — "False positives I caught" section.

- **Don't design event schemas from imagination**: our original Pydantic event schema matched nothing the real `claude` CLI emits. The first session ran for 6 hours building parsing and streaming before a smoke test caught it. Cost: a full extra design pass (`cli_translator.py`).
- **Rule**: capture real output FIRST. Run the tool you're integrating with. Only then write a schema. Treat your assumptions about external systems as guilty until proven innocent by stdout.
- **Where it applied**: `backend/app/cli_translator.py` (the patch that should not have been necessary).

- **Compliance theater is worse than no compliance**: the UI showed "MNPI walls: ON" and "Entitlements: ..." while nothing enforces them. A real buy-side analyst clocks this in 30 seconds and loses trust in the rest of the product. Same with `⌘K` as a dead `<span>` and a fake `opus-4.7 ▾` model selector.
- **Rule**: if a UI element implies a guarantee, either deliver the guarantee or remove the element. Never leave decorative compliance/trust signals in the product. Even in pre-pilot demos.
- **Where it applied**: `frontend-react/src/components/frame/{BrandBar,ComplianceBar,StatusBar}.tsx`, `PromptInput.tsx` (opus-4.7).

- **The Internal-DAU gate is real and easy to skip**: the project has 32 commits over ~3 weeks, none of which are "I used Quant Agent today and noticed X." Per Cat Wu / Anthropic, products that haven't been used daily by their author for 7 consecutive days aren't ready.
- **Rule**: schedule the dogfooding before shipping more features. Skip-a-day-reset-the-counter is the discipline; commits don't substitute for use.

- **Wiki only compounds knowledge if it's used**: `wiki/log.md` has 1 entry (the initialization). The Karpathy pattern is right but the discipline is the part that's missing. This audit is going INTO `wiki/log.md` as part of the close-out.

## (template, append here)

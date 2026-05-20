# ADR 0001 — Use the Claude Code CLI subprocess, not the Anthropic SDK

**Status:** Accepted (2026-04-29)
**Deciders:** Saurabh Jalendra
**Context source:** `CLEANUP_SUMMARY.md`, `wiki/concepts/claude-code-cli-vs-sdk.md`

## Context

Initial implementation wired `anthropic` Python SDK directly: a custom system prompt, a hand-written tool-use loop, hand-implemented tool executors for file/git/bash/grep (~700 LOC under `tools/`). Maintaining the agentic loop ourselves was a lot of code that already exists in the official `claude` CLI.

## Decision

Replace the SDK-based agent with a subprocess wrapper around the official `claude` CLI invoked per chat message:
```
claude -p "<prompt>" --output-format stream-json --verbose --dangerously-skip-permissions
```
The CLI handles tool execution, planning, sub-agent dispatch, MCP integration, and permission gating. We parse its `stream-json` stdout into our typed event schema and fan out via SSE.

## Consequences

**Positive**
- ~700 LOC of tool executor code deleted.
- Tool surface (Read, Write, Edit, Bash, Grep, Glob, WebSearch, WebFetch, MCP) inherited for free.
- New CLI features land without us shipping anything.
- The CLI's permission model and skill ecosystem (Superpowers etc.) are usable without integration work.

**Negative**
- Tied to the CLI's output contract. Our `cli_translator.py` exists because CLI events don't match our initial guess at the schema — every CLI version risks needing translator updates.
- `--dangerously-skip-permissions` is mandatory in practice (we have no UI for tool approval). All safety relies on workspace isolation.
- Auth via `~/.claude/config.json` files baked into the container image — token rotation is painful.
- May violate Claude Code ToS for non-personal use (per `CLAUDE_CODE_SETUP.md`). Acceptable for the current personal/local pilot.
- No streaming partial-tool-result granularity; we get whole assistant/tool_use/tool_result chunks.

## Alternatives considered

1. **Stay on Anthropic SDK.** Rejected: keeping pace with the CLI's tool ecosystem and skill system is unrealistic at solo-dev throughput.
2. **Anthropic SDK + Managed Agents API** (when GA). Rejected for v1 as the API surface wasn't stable enough in early 2026. Worth revisiting in v2.
3. **OpenAI / multi-provider abstraction.** Rejected — provider-neutrality is not a goal; the product is opinionated about Claude.

## Reversal criteria

Switch back to SDK if:
- Anthropic publishes a stable Managed Agents API with feature parity to the CLI.
- ToS becomes restrictive for commercial use.
- The CLI starts emitting unstable / breaking schema changes faster than the translator can keep up.

## References

- Migration commits: `267487c` (CLI translator), `909c62b` (ClaudeCodeService rewrite), `8f356c2` (--verbose flag fix).
- See `wiki/entities/claude-code-service.md` for the implementation.

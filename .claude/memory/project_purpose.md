---
name: Project Purpose
description: What Quant Agent is, its goals, and key constraints
type: project
---

# Project Purpose

## What it is

A locally-hosted Claude AI coding chatbot. The user chats in a React UI; the backend spawns a per-session `claude` CLI subprocess inside an isolated git workspace; the agent does file ops, git, and bash inside that sandbox.

## Architectural choice (key)

The project deliberately uses the **Claude Code CLI** as its agent runtime instead of the Anthropic SDK. ~700 LOC of native SDK + custom tool executor was deleted in favor of `ClaudeCodeService` (~235 LOC) wrapping `claude -p ... --output-format json`. See `CLEANUP_SUMMARY.md`. This trades fine-grained control for offloading the entire tool-use loop to the CLI.

## Goals

- Single-developer/local use — not multi-tenant, not production-exposed.
- Per-session workspace isolation so the agent can clone arbitrary repos without polluting the host.
- Auto-cloned default repo (`DEFAULT_REPO_URL` in `.env`) so a fresh session has something to work on immediately.

## Constraints

- **Personal project** (confirmed 2026-04-29) — solo developer, broad permissions OK, no team review process needed.
- Authenticated via OAuth-style tokens (`CLAUDE_CODE_ACCESS_TOKEN` + `_REFRESH_TOKEN`), not an API key.
- Status: experimental. May violate Claude Code ToS without explicit Anthropic approval (per `CLAUDE_CODE_SETUP.md`).

## What it is NOT

- Not a hosted SaaS — no auth, no multi-tenancy, CORS is `*`.
- Not a replacement for Claude Code CLI itself — it's a chat wrapper around it.
- Not test-covered — `test_endpoint.py` / `test_imports.py` are debug scaffolding, not pytest.

## To fill in

What is the next thing you want to build or fix? Update CLAUDE.md "Current Focus" once decided.

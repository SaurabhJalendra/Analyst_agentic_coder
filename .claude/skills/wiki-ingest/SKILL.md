---
name: wiki-ingest
description: Add a new source (paper, doc, transcript, takeaway) to the project wiki. Reads the source, discusses takeaways with the user, writes a summary, updates 10-15 existing pages, creates stubs, refreshes the index, appends the log.
allowed-tools: [Read, Write, Edit, Grep, Glob, Bash, WebFetch]
---

# Wiki Ingest

This is the **canonical workflow** from `wiki/SCHEMA.md`. Read SCHEMA.md before every run — it evolves.

## Step 0 — Read the schema

```
Read wiki/SCHEMA.md
```

If the schema has changed since you last read it, follow the new rules.

## Step 1 — Capture the source

Identify what's being ingested:
- **A file the user uploaded or pointed at** → read it in full.
- **A URL** → WebFetch it.
- **An idea or session takeaway** → ask the user to write 1-3 paragraphs of source text first, so we have something concrete to cite.

Save the raw text to `wiki/sources/YYYY-MM-DD-<slug>.md` with frontmatter:

```yaml
---
title: <human-readable title>
url: <if applicable>
ingested: YYYY-MM-DD
kind: paper | doc | transcript | note
---
```

The slug is lowercase kebab-case derived from the title.

## Step 2 — Discuss takeaways

**Stop and talk to the user.** Print:

1. A 3-sentence summary of what the source says.
2. **3–5 takeaways** ranked by relevance to *this project* (Quant Agent).
3. For each takeaway, the wiki pages it would touch.

Wait for the user to confirm or redirect before writing pages. Users curate; LLMs do bookkeeping.

## Step 3 — Write the summary page

If the source is substantial (>500 words, dense, or a paper):

Create `wiki/synthesis/<slug>-summary.md` with:
- Frontmatter (`type: synthesis`, source citation)
- Summary section
- "Key claims" with citations into the source file
- "Implications for this project" section
- Links to pages that will be updated

If the source is small (a quick note), skip this step and inline the takeaway into existing pages.

## Step 4 — Update existing pages (the heavy lift)

**Aim for 10–15 pages touched.** This is what makes the wiki *compound*. Each page touched:

1. Bump `updated: YYYY-MM-DD` in frontmatter.
2. Add new claim(s) with citations: `... (source: ../sources/<slug>.md)` or `... (source: <url>)`.
3. Add new `[[wikilinks]]` if the source introduced relationships.
4. If a claim now contradicts an existing claim, **don't silently overwrite**. Add the new claim, mark the old one with `[contradicted-by: <new-claim-anchor>]`, and log the contradiction in `log.md`.

Use Grep over `wiki/concepts/` and `wiki/entities/` to find candidate pages by keyword.

## Step 5 — Create stubs for new things

If the source introduced an entity or concept that has no page yet:

Create `wiki/concepts/<slug>.md` or `wiki/entities/<slug>.md` with:
```yaml
---
title: <name>
type: concept | entity
created: YYYY-MM-DD
updated: YYYY-MM-DD
sources: [<source>]
status: stub
---

## Summary

[stub — to be expanded]

## Sources

- ../sources/<slug>.md
```

Don't fill them out unless the user asks. Demand drives depth.

## Step 6 — Refresh the index

Open `wiki/index.md` and add lines for any new pages, in the right category. Update the "Stats" footer.

## Step 7 — Append the log

Open `wiki/log.md`. Append a new entry **at the bottom** with this format:

```markdown
## YYYY-MM-DDTHH:MM — short title

**Trigger:** ingest

**Source:** [[../sources/<slug>|<title>]]

**Pages touched:** [[concept-1]], [[entity-2]], ...

**Pages created:** [[new-stub-1]], [[new-stub-2]]

**Key claims added:**
- claim 1 (cites: source)
- claim 2

**What changed in understanding:** one-sentence delta.

---
```

Never edit a past log entry. Append-only.

## Step 8 — Report back

Tell the user:
- N pages touched, M pages created (stubs).
- Top 3 most important new claims, with the page each lives on.
- Any contradictions flagged.
- Any open questions added that they should consider.

## Hard rules (from SCHEMA.md)

1. The wiki persists between sessions. Don't regenerate from scratch.
2. Don't decide what to read on the user's behalf. They curate sources.
3. Citations ground claims. Bare claims are debt — mark with `[needs-source]` if you can't cite.
4. `log.md` is append-only.
5. `sources/` is immutable.

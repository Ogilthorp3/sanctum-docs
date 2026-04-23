# AGENTS.md

You are an AI agent (Claude, Codex, Cursor, Aider, Gemini CLI, or other)
being asked to write or edit documentation in this repository. Before you
touch an MDX file, read **[CONTRIBUTING.md](./CONTRIBUTING.md)** in full.
It is the source of truth for voice, structure, images, and the rules
that will fail your commit if you violate them.

This file exists because AI agents too often skip straight to the edit.
The five rules below are the ones that break most often and fail fastest
in CI. None of them are suggestions.

## The five you can't skip

1. **Every new page has a unique hero image.** Pencil sketch, dark background,
   one teal or amber accent halo. Generate with `tools/gen_hero_image.py` in
   the parent Claude_Code repo. The image goes in `<category>/images/` next
   to the page. No SVGs for heroes. No stock photos. No clip art.

2. **No emojis in prose.** The only allowed files are the Holocron portal
   pages — `index.mdx`, `index-qc.mdx`, and `qc.mdx` — which use `⚜` and
   `🐻` as semantic brand glyphs (Québec fleur-de-lis, black bear). On
   every other page: tables, headings, and prose are emoji-free. Status
   markers go in as words: `RUN / SCHED / FAIL / OFF`. No `✅ ❌ 🔴` in
   content pages.

3. **Five-Minute Rule.** ≤ 1200 prose words per page. Tables and code blocks
   don't count against it. If the page is longer, split the long material
   into an annex under `operations/` and link to it.

4. **Haus, not house.** See the "Haus Rule" section of CONTRIBUTING for the
   full mapping. Exceptions: product names (Home Assistant, HomeKit), file
   paths (`/home/ubuntu/`), idiomatic English ("makes house calls"), and
   the category terms (home office, home router, home server).

5. **No placeholder text.** Never `example.com`, `YOUR_TOKEN_HERE`, `<placeholder>`,
   or similar. Use the real Sanctum default — real ports, real paths, real
   model IDs, real endpoint names. If you don't know the real value, stop
   and ask before you ship fiction.

## Before you commit

Run the checker on what you changed:

```bash
python3 scripts/contrib-check.py src/content/docs/path/to/your-page.mdx
```

It validates the rules above plus frontmatter completeness and hero-image
file presence. Exit 0 means you're clear; exit 1 means you have to fix
something before the PR merges. The same check runs in GitHub Actions on
every PR.

## When in doubt

Read the section of CONTRIBUTING.md that covers your situation. The
table of contents covers voice, structure, illustrations, Québécois,
ports, and the Tommy standard. The last one is the tiebreaker: if Tommy
the dead cat wouldn't approve your page, rewrite it until he would.

## Tool-specific notes

- **Claude Code** loads `CLAUDE.md` at repo root (symlinked to this file).
- **Codex / Aider** load `AGENTS.md` directly.
- **Gemini CLI** loads `GEMINI.md` (symlinked to this file).
- **Cursor** reads `.cursorrules` (symlinked to this file).

All four symlinks point here so there is one file to update.

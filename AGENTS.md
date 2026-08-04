# AGENTS.md

You are an AI agent (Claude, Codex, Cursor, Aider, Gemini CLI, or other)
being asked to write or edit documentation in this repository. Before you
touch an MDX file, read **[CONTRIBUTING.md](./CONTRIBUTING.md)** in full.
It is the source of truth for voice, structure, images, and the rules
that will fail your commit if you violate them.

This file exists because AI agents too often skip straight to the edit.
The eight rules below are the ones that break most often and fail fastest
in CI. None of them are suggestions.

## The eight you can't skip

1. **Every new page has a unique hero image.** Pencil sketch, dark background,
   one teal or amber accent halo. Generate with `tools/gen_hero_image.py` in
   this repo (`sanctum-docs/tools/`) — the single canonical generator; there
   is no copy in the parent Claude_Code repo. The image goes in
   `<category>/images/` next to the page. No SVGs for heroes. No stock
   photos. No clip art. **Unique means visually unique**: never reuse another
   page's art and never near-duplicate a composition — the deploy gate runs
   `python3 tools/hero-dupe-check.py . 10` (perceptual hash; needs `pillow`)
   and fails on any two pages whose heroes look alike, even with different
   bytes. Regenerate the duplicate; do not lower the threshold.

2. **No emojis in prose.** The only allowed files are the Holocron portal
   pages — `index.mdx`, `index-qc.mdx`, and `qc.mdx` — which use `⚜` and
   `🐻` as semantic brand glyphs (Québec fleur-de-lis, black bear). On
   every other page: tables, headings, and prose are emoji-free. Status
   markers go in as words: `RUN / SCHED / FAIL / OFF`. No `✅ ❌ 🔴` in
   content pages.

3. **Chapter Rule.** ≤ 1600 prose words per page, 2000 hard ceiling. Tables,
   code blocks and the annex don't count against it. If the page is longer,
   split the long material into an annex under `operations/` and link to it.
   (Raised from 1200 on 2026-07-29 — the Narrative Standard made a cold open
   and a landing mandatory, and that budget must not come out of the content.)

4. **Haus, not house.** See the "Haus Rule" section of CONTRIBUTING for the
   full mapping. Exceptions: product names (Home Assistant, HomeKit), file
   paths (`/home/ubuntu/`), idiomatic English ("makes house calls"), and
   the category terms (home office, home router, home server).

5. **No placeholder text.** Never `example.com`, `YOUR_TOKEN_HERE`, `<placeholder>`,
   or similar. Use the real Sanctum default — real ports, real paths, real
   model IDs, real endpoint names. If you don't know the real value, stop
   and ask before you ship fiction.

6. **Escape `<digit` in MDX.** A `<` followed by a digit (or any non-letter)
   is parsed as the start of a JSX tag and crashes the Astro build with
   `Unexpected character ... before name`. Pure prose like `<20%` or
   `<3 attempts` is the most common case. Three valid fixes:
   `&lt;20%`, `` `<20%` `` (inline code), or reword to `under 20%`.
   `contrib-check.py` will catch this locally before the deploy does.
   **Table cells have a second trap:** a raw `|` inside a table cell splits
   the cell *even inside backticks*, so a chat token like `` `<|im_start|>` ``
   in a table dangles a `<` and kills the build. Write `` `<\|im_start\|>` ``.
   (Cause of the 2026-07-30 deploy break; `contrib-check.py` now catches it.)

7. **The Narrative Standard is gated.** `story-check.py` is the other half of
   the checker: every page needs a cold-open hook (never "This page
   describes..."), a spine, someone in the room, a real landing, and lineage
   links. Errors block the deploy. The gold standard is `agents/tommy.mdx` —
   match the craft, not the first person (rule: you are not Tommy unless you
   are Tommy). Frame carries the story; reference/config bodies stay dry.

8. **Vary the music.** The corpus is watched by `scripts/echo-audit.py`
   (weekly, advisory): a device repeated across the book stops being a
   surprise. Don't default to a clock-time cold open ("It is 2 AM...") and
   don't land on Tommy unless the page has *earned* him — as of 2026-07-31
   both are over budget corpus-wide. Reach for the page's OWN imagery: open
   inside its subject, land on a callback to its opening.

   **The bolted-cameo trap.** `cast/alt-text-cameo` fires when a character is
   named only in your alt text, and the cheapest way to clear it is to bolt a
   Tommy sentence onto the last line. Do not do that. The 2026-07 sweep did it
   54 times and the audit now measures it directly (`BOLTED cameo`): a landing
   that names someone who appears nowhere else on the page is a stage exit for
   an actor who was never in the scene. Either give the character a real beat
   in the body, or land on the page's own subject and leave the cast out.

## Before you commit

Run BOTH checkers on what you changed, then build:

```bash
python3 scripts/contrib-check.py src/content/docs/path/to/your-page.mdx
python3 scripts/story-check.py  src/content/docs/path/to/your-page.mdx
npm run build   # the only gate that catches every MDX crash class
```

contrib-check validates correctness (frontmatter, hero presence, leaks,
MDX traps); story-check validates the narrative shape (hook, spine, cast,
landing, lineage). Exit 0 on both means you're clear; errors block the PR
gate AND the deploy gate. If you generated a hero, also run
`python3 tools/hero-dupe-check.py . 10` (needs `pillow`) — the deploy
fails on visually-duplicate art. If you touched the checkers themselves,
`python3 -m pytest tests/ -q` must stay green: it pins the calibration
contract (Tommy = exactly one permanent warning).

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

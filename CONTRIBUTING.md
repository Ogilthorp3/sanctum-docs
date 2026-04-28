# Contributing to Sanctum Docs

You want to write documentation for a haus automation platform that takes itself exactly seriously enough. Good. Here's how.

## Voice & Tone

Sanctum docs are technically precise and dryly self-aware. The humor comes from the gap between enterprise infrastructure and a haus in Québec — never from trying to be funny.

**The formula:** Lead with the technical fact. Follow with the human observation.

> "The watchdog checks every service every ten minutes, attempts to fix what's broken, and tells you about whatever it couldn't fix."

> "It is also, let's be honest, a $1,600 space heater that happens to control the other space heaters."

The last sentence of a section often lands a quiet punchline. Don't force it. If the section doesn't earn one, end on the technical fact and move on.

**Pronouns:** "We" for the product, "you" for the reader. Tommy pages are first-person singular — irreverent, feline, devastating. You are not Tommy unless you are Tommy.

**Warmth matters.** There is genuine love for this project under every quip. The humor punches at the absurdity of the situation, never at the reader.

## The Five-Minute Rule

A doc page should be readable in five minutes. Not skimmed — read. That's the budget.

Five minutes is roughly 1,000 words, or about 150 lines of prose once you account for headings, code blocks, and the asides that make the page worth reading in the first place. If your page runs longer, it isn't a page anymore — it's a filing cabinet pretending to be one.

**What this means in practice.** Architecture pages explain the idea and stop. Operational material — dated incidents, forensic walkthroughs, the thing that took four hours on a Tuesday — goes in its own annex under `operations/` and gets linked from the parent page. The doctrine page keeps the doctrine. The annex keeps the receipts.

**Why this rule exists.** A reader who bounces off a 3,000-word page learns nothing. A reader who finishes a 900-word page and follows one link into the archive learns twice. The shorter page respects the reader's time, which is the only currency documentation actually trades in.

**Exceptions.** A few chapters earn a longer read because they are structurally load-bearing — the Living Force is the standing example, and it runs long because the Ten Principles have to stay whole or the architecture doesn't make sense. Exceptions are earned by the chapter's role in the overall map, not by the author's affection for their own prose. If you think your page is the exception, get a second opinion before you skip the budget. Most pages that feel load-bearing to their author are filing cabinets in denial.

## Page Structure

Every page is MDX with this skeleton:

```mdx
---
title: The Thing
description: What the thing does, in one sentence.
---

import { Aside, Card, CardGrid, Steps, Tabs, TabItem } from '@astrojs/starlight/components';

![Descriptive alt text that adds personality](./images/hero-the-thing.png)

Opening paragraph. Hook the reader. Acknowledge the absurdity if there is absurdity to acknowledge.

## How It Works

Technical content. Real config. Real ports. Real commands.

## Configuration

```yaml
# Actual config blocks — never pseudocode
service:
  port: 18094
  enabled: true
```

<Aside type="caution">
Things that will bite you go here. Be specific about the bite.
</Aside>
```

**Aside types:**
- `note` — interesting technical detail or fun fact
- `tip` — genuinely useful advice
- `caution` — things that will bite you
- `danger` — things that will destroy you (used sparingly, earned)

Every Aside should have personality. "Don't do this" is a warning. "This will silently eat your config at 3am and you will blame DNS" is a Sanctum warning.

## Code Examples

Real **ports**. Real **paths** (with the canonical username — see below). Real **service names**. Everything else — IPs, MAC addresses, hostnames, phone numbers, tokens, UUIDs, email addresses, personal identifiers — uses the canonical placeholders. If a reader can use your code example to find the haus on a network, you have failed the reader and the haus.

If you write `example.com` or `YOUR_TOKEN_HERE` you have also failed, just differently. Use the canonical Sanctum placeholders below — they're realistic enough to teach the pattern and useless for reconnaissance.

YAML blocks for configuration. Shell blocks for commands. Annotate with comments when the config isn't self-evident, but don't narrate the obvious.

## The No-Leak Rule

Docs ship to a public repo. Assume a hostile reader. The following never appear in a docs page, in any commit, in any git branch:

- **Real IP addresses** — no tailnet (`100.x.x.x`), no LAN (`192.168.x.x`), no VM bridge (`10.10.10.x`), no public IPs. Use the documentation ranges below.
- **Real MAC addresses** — every one enables device fingerprinting. Use the `AA:BB:CC:DD:EE:xx` block, which is IANA-reserved for documentation.
- **Real hostnames** — no `Firstname-Mac-Model.local` patterns, no instance slugs tied to the owner (`<firstname>-nepveu` etc.), no `*.local` that actually resolves on the owner's tailnet. Use the host placeholders.
- **Real usernames** — the canonical owner handle is **`neo`**. Paths use `/Users/neo/` or `~/`, never the operator's actual login name.
- **Phone numbers** — use `+15555550100` style (the `555-0100`–`555-0199` block is reserved for fiction).
- **Tokens, API keys, bearer secrets** — the file *path* to a secret is fine; the *value* is never. Not even revoked values — they correlate with other logs.
- **UUIDs tied to real accounts** — Apple notarization IDs, App Store Connect IDs, hardware UUIDs, anything that could be cross-referenced with a leak elsewhere.
- **Email addresses** — use `<owner@haus>`.

Canonical placeholder registry:

| Concept | Placeholder | Notes |
|---|---|---|
| Owner username | `neo` | Matches the public GitHub org. Use in paths, `ssh` targets, prompts. |
| Owner home | `/Users/neo/` or `~/` | Prefer `~/` in prose; full path only when the file path itself matters. |
| Owner email | `<owner@haus>` | |
| The Mini (server) | `<MINI>` or `manoir.local` | "manoir" is the slug; `.local` is an mDNS placeholder, not a real resolvable host. |
| The MacBook (road warrior) | `<MBP>` or `satellite.local` | |
| The VM (OpenClaw / Yoda) | `<VM>` or `yoda` (as the `ssh` alias) | |
| Mac ↔ VM bridge | `10.0.0.1` / `10.0.0.10` | RFC 5737 documentation range — never resolves, never routes. |
| Tailnet address | `100.0.0.X` | Visually obvious placeholder; Tailscale's real range is 100.0.0.0/10. |
| Home LAN address | `192.0.2.X` | RFC 5737 TEST-NET-1. |
| MAC address | `AA:BB:CC:DD:EE:XX` | Use `:01`, `:02`, `:03` for distinct devices. IANA documentation prefix. |
| Phone number | `+15555550100` | 555-0100 through 555-0199 is the fictional-use block. |
| Signal account | `+15555550100` | Same block. |
| API token | `sk-placeholder-do-not-use` | Token *paths* are fine (`~/.sanctum/secrets/X.token`); token *values* never. |

**Before you commit**, grep your diff. If you wrote an IP that isn't in the 10.0.0.0/24, 192.0.2.0/24, or 100.0.0.0/24 blocks, you wrote a real one. Fix it. The CI check runs `scripts/contrib-check.py` which flags these patterns; treat a failure as a security incident, not a style nit.

## The Haus Rule

Sanctum uses **haus** instead of "house" or "home" when referring to the dwelling. It's the brand voice — German-inflected, deliberate, and consistent. The tagline is "Your haus, wittily managed." The docs follow.

**Change to "haus":**
- "your house" → "your haus" (the dwelling running Sanctum)
- "the house" → "the haus" (when it's *this* haus)
- "home automation" → "haus automation" (the domain, Sanctum-style)
- "home intelligence" → "haus intelligence"
- "someone is home" → "someone is haus"
- "vacation house" → "vacation haus"
- "household" → "haushold" (the dwelling + the people in it — the whole unit)
- "households" → "hausholds" (plural of the same)

**Keep as-is:**
- **Home Assistant** — product name, always capitalized, never touched
- **HomeKit**, **Apple Home** — product names
- `/home/ubuntu/` — file paths are file paths
- **"home office"**, **"home router"**, **"home server"** — standard English category terms
- Idiomatic expressions where "house" is the joke — "makes house calls", "burning your house down"
- Generic analogies about houses in general — "like every room in a house that lost power"

When in doubt: if the sentence is about *this specific dwelling running Sanctum*, it's a haus. If it's about houses in general or a product name, leave it.

## Québécois Guidelines

The French pages are Québécois joual — not Parisian French with a flannel shirt.

| Write | Not |
|-------|-----|
| chu | je suis |
| icitte | ici |
| astheure | maintenant |
| pis | et |
| pantoute | pas du tout |
| cabane | maison |
| brunante | crépuscule |

Technical terms stay in English. Nobody says "conteneur Docker" with a straight face.

The QC version is not a translation. It is a rewrite. Same structure, same Asides, same code blocks — but the prose is reborn in the voice. If you wouldn't say it out loud in a dépanneur, rewrite it.

## Illustrations

Every doc page gets one unique hero image. No exceptions. No SVGs. No stock photos. No clip art.

### The Style (Phase 2)

As of April 2026, illustrations follow a **section-aware hybrid style**:

#### Architecture Section — Hybrid Style

The architecture section uses a **two-tier visual language**:

1. **Hero images (top of page):** Colorful, cinematic sci-fi concept art. Full color with teal/amber lighting. These are the eye candy — they draw you in. Think movie poster meets technical blueprint.

2. **Inline illustrations (within the prose):** Pencil-sketch technical drawings on dark paper. One subtle teal or amber accent halo. These explain — they're the technical diagrams that make you understand the architecture while making it look gorgeous.

This hybrid approach gives each architecture page a visual arc: colorful hook → technical depth with hand-drawn illustrations that feel like they were sketched on a napkin by an engineer who happens to be an artist.

#### All Other Sections — Pencil Sketch

Everything outside the architecture sidebar (guides, operations, reference, agents, getting-started) uses the **pencil sketch** format for all images:

- **Format:** Square or Wide (~16:9) pencil sketches.
- **Background:** Dark / Black.
- **Lighting:** One subtle localized color halo (Teal or Amber).
- **Lines:** Clean, technically precise but with a hand-drawn pencil feel.
- **Themes:** Digital horizons, technical interfaces, and metaphors for automation.

#### Universal Rules

- **Uniqueness:** **Never** reuse a hero image from another page.
- **ASCII art is allowed when — and only when — it renders beautifully on every device and every resolution.** Mobile to 4K, small font to large zoom, light theme to dark. In practice that means keeping diagrams under ~50 characters wide (so a phone viewport doesn't force horizontal scroll), using only standard box-drawing glyphs (`├ ┤ ┬ ┴ ─ │ ┌ ┐ └ ┘ ▲ ▼ ◀ ▶`), and previewing on a narrow window before shipping. If your diagram needs more width, relies on non-monospace kerning, or reads awkwardly at any common font size, it has outgrown ASCII — reach for an SVG. The rule is aesthetic integrity, not medium purity. Terminal output samples (where ASCII is what the user actually sees) are always fine.

### Generation Tool

We use a centralized tool in the main repository to generate these via **Google Gemini / Imagen**.

```bash
# From the root of Claude_Code
python3 tools/gen_hero_image.py "Your detailed prompt here..." src/content/docs/[path]/images/hero-name.png
```

The tool automatically:
- Pulls the API key from macOS Keychain (`gemini-api-key` or `Google AI Studio`).
- Uses the best available Imagen/Gemini model for image generation.
- Outputs PNG to the specified path.

**Never use Rube/Composio for image generation.** Rube is deprecated. Use `gen_hero_image.py` or direct Gemini API calls via the keychain-stored API key. All external service access uses direct APIs or native MCP integrations — no intermediary platforms.

### Prompt Templates

**For architecture heroes (colorful):**

`[Subject Description]. Cinematic sci-fi concept art, dark background, volumetric lighting, teal and amber accent colors, no text, no words, no letters.`

> Example: "A futuristic holographic routing switchboard in a dark command center. Three glowing neural pathways branch from a central node — one teal, one amber, one white. Each path leads to a different floating brain made of circuits. Cinematic sci-fi concept art, dark background, volumetric lighting, no text."

**For architecture inline illustrations (pencil sketch):**

`[Subject Description]. Technical pencil sketch, dark background, clean lines, [Teal/Amber] localized accent lighting, hand-drawn feel, no text.`

> Example: "Golden filaments merging into neural network nodes at each layer. Technical pencil sketch, dark background, amber accent, no text."

**For all other sections (pencil sketch heroes):**

`[Subject Description]. Cinematic sci-fi concept art, dark background, clean lines, pencil sketch style, [Teal/Amber] localized accent lighting, no text.`

> Example: "A technical pencil sketch of a secure communication device projecting a holographic signal wave. Detailed circuitry and antenna patterns visible. Dark background, soft amber glow, clean lines, no text."

### Alt Text

Alt text must describe the scene **and** have personality. It's both accessibility and brand voice:

```
Good: "Sanctum Proxy — a technical pencil sketch of a secure gateway gatekeeper with glowing teal authentication nodes."
Bad:  "An image of a server with some lights."
```

### Consistency Checklist

Before committing a new illustration, verify:

- [ ] Black/dark background with one subtle, localized color halo (Teal or Amber).
- [ ] Pencil sketch / hand-drawn line quality.
- [ ] Wide or Square format.
- [ ] Metaphor is immediately readable without explanation.
- [ ] Technical concept is embedded in the visual (not just decorative).
- [ ] File is real PNG (not JPEG with .png extension).
- [ ] **Image is unique** — not used on any other page.

### Do Not

- **No SVGs for hero images.** SVGs are for inline technical flow diagrams only.
- **No fully colorized illustrations outside architecture heroes.** The pencil sketch sections use accent halos only.
- **No Rube/Composio for image generation.** Direct API via keychain only.
- **No placeholder images.**
- **No ASCII art that breaks on mobile.** ASCII is allowed — see the aesthetic-integrity rule above — but only when it renders beautifully on every device. If it requires horizontal scroll on a phone, it needs to be narrower or it needs to be an SVG.
- **No stock photos, clip art, or generic AI imagery.** Every image must be specific to Sanctum.

### Architecture Section — Specific Visual Rules

The architecture pages in the sidebar have the highest visual bar. Each page should have:

1. A **colorful hero** at the top (16:9, cinematic sci-fi)
2. At least one **pencil-sketch inline illustration** within the technical content
3. **Tables over prose** for specs, ports, and configurations
4. **SVGs** for complex flow diagrams (not ASCII art in code blocks)

The visual arc should feel like: "wow, that's beautiful" (hero) → "oh, I understand how this works" (inline sketch) → "I can actually configure this" (tables and code blocks).

Think of it as: the hero gets you in the door, the pencil sketch keeps you reading, and the code block makes you productive.

## Port Naming — The Deadpool Convention

Every service needs a port. Most infrastructure assigns them sequentially and moves on. Sanctum doesn't, because if you're going to memorize port numbers at 2 AM in your underwear, they should at least be memorable.

**The rule:** Name the ports you chose. Leave the ports that chose you.

Ports you deliberately picked — 1337, 1977, 1984, 4040, 4077, 4078, 8008, 10101, 31416, 42069, 42070 — have cultural references or deliberate wit. They get codenames and one-liner commentary in the Port Summary table. These are creative decisions that deserve documentation.

Ports that are defaults (22, 8123) or sequential allocations (18080/18081/18085) didn't earn a story. They get dry observations about their own existence. The humor in a default port is acknowledging that it's a default. Don't force a cultural reference onto a number that's just doing its job.

**How to pick a port number for a new service:**

1. **Check if it's free.** `lsof -iTCP:<port> -sTCP:LISTEN` on Mac, `ss -tlnp` on VM. Also check `expected-ports.json` in the council-router config.
2. **Must be above 1024.** Anything below requires root to bind. LaunchAgents run as the user.
3. **Cultural reference preferred.** A year, a movie, a song, a math joke — something a human can latch onto. The port number is infrastructure _and_ documentation. When someone sees 4077 in a log, they should think "that's Force Flow" without checking a spreadsheet.
4. **No explanation required.** If the reference needs a paragraph to land, pick a different one. 1977 (Star Wars) works. 1895 (year Marconi sent the first wireless signal) does not. The test: would someone in the room get it without Googling?
5. **Update the Port Summary table.** Every new port gets a row with a Codename and Commentary. The commentary is one sentence — technically accurate, culturally aware, and exactly as amused as the situation warrants.
6. **Add a `# port_lore:` comment to the service YAML.** Place it directly under the `port:` field in `~/.sanctum/services/<name>.yaml`. This is the source-of-record for the gag. Format: `# port_lore: <one sentence>`. It is an optional comment — the watchdog schema ignores it, but the next human at 2 AM will not.
7. **Update `expected-ports.json`.** The council-router test suite validates that expected ports are listening. A new service that isn't in the list will trigger a Windu security alert.

## Typography

Body text is justified (`text-align: justify`) **on every page including the landing page** at `sanctum.run`. Combined with `hyphens: auto` and `text-justify: inter-word`, this gives clean left and right edges across all documentation without ugly inter-word rivers on narrow viewports.

The rule lives in `src/styles/custom.css` under `.sl-markdown-content` and the `[data-has-hero]` overrides. Do not override it with centered or left-aligned prose blocks — the justified layout is doctrine, not decoration. UI elements rendered outside `.sl-markdown-content` (Starlight's hero tagline, CTA buttons, navigation, logos) keep their template-default centering; only the body prose justifies.

If you add a new wrapper class for prose content, justify it. If you find a wrapper that left-aligns or centers prose, fix it.

## Technical Accuracy — Current Architecture

Keep these facts current across all docs. If any page contradicts these, it's stale and needs updating:

**VM Hypervisor:** QEMU headless (not UTM — UTM was removed). The LaunchAgent is still named `com.sanctum.utm-autostart` (identifier preserved for compatibility).

**Model Routing** (updated 2026-04-23 after Olympics rework):
- **Local default — `council-secure`** (Qwen3.6-35B-A3B on `:1337` mTLS): Yoda, Mothma, Windu, Cilghal, Mundi, Jocasta. The 35B-A3B is Olympics rank #2 (0.957) and wins on uniformity; house default.
- **Coder tier — `coder`** (Qwen2.5-Coder-14B via LM Studio `:1234`): Qui-Gon, Ahsoka. Ahsoka runs on a 16 GB M1 at the chalet and can't fit the 35B; Qui-Gon wants tight code gen at 22 tok/s.
- **Cloud escalation — `cloud`** (Claude Opus 4.7 via `claude-max-api-proxy` on `:3456`, OpenRouter fallback): Yoda and Mundi only, for novel reasoning and complex finance edge cases. Uses the Max subscription OAuth — zero API credits consumed for routine calls.
- **Spatial escalation — `spatial`** (Gemini 3.1 Pro via Google AI Studio Ultra): Windu only, for network topology / zone map / physical layout reasoning.

Config lives in `~/.sanctum/instance.yaml` under `router:`. Full per-Jedi rationale and Olympics-informed justification: see [The Smart Router](./src/content/docs/architecture/dynamic-model-routing.mdx).

**Key Services:**
- sanctum-server (Rust): Smart Router with pattern/intent dispatch
- sanctum-mlx (Rust): Native inference with LoRA adapter merging
- sanctum-cloud-proxy (Python): Cost-capped Opus access with fallback chain
- Model Tournament: Automated eval + deploy of new model candidates

**External Service Access:** Direct APIs only. No Rube/Composio. API keys stored in macOS Keychain. Image generation via Gemini API (keychain-stored key). Slack via webhook. Outlook via Microsoft 365 MCP.

**Testing:** 178 tests across 11 components. Nothing ships without tests.

**Service catalogue:** 38 services as of 2026-04-18. Watchdog reports `overall: healthy` at 38/38. Service YAMLs live in `~/.sanctum/services/`. The guardrail script `tools/catalogue-sync-check.sh` cross-references running TCP ports against the watchdog catalogue — run it after any `launchctl load` that isn't accompanied by a YAML commit.

**OBLITERATUS:** Uses `venv/` (non-hidden), Python 3.12, port 7860. Never `.venv/` — Python 3.14 silently breaks editable installs in hidden directories.

**Q2 renames (effective 2026-Q2):** `xtts` → `xtts_server`, `gateway` → `openclaw_gateway` throughout `instance.yaml` service keys, service YAML filenames, and test harnesses.

## What Not To Do

- **No marketing language.** "Seamlessly orchestrates" is a firing offense.
- **No buzzwords.** If you write "leverage" as a verb, the watchdog will find you.
- **No emojis in prose.** The holocron portal gets emojis. Nothing else does.
- **No explaining obvious things.** If the reader needs to be told what YAML is, they're not here yet.
- **No placeholder text.** Every sentence earns its place or it doesn't exist.
- **No mean-spiritedness.** We laugh at the absurdity of running Kubernetes-grade monitoring for a thermostat. We never laugh at someone for not knowing how.
- **No lazy QC translations.** If the French reads like Google Translate with a tuque on, start over.

## The Tommy Standard

Tommy's pages are written as if by a dead cat who has strong opinions about network segmentation. They are the gold standard. If your page wouldn't survive Tommy's editorial review — if it's generic, or timid, or tries too hard — revise it until it would.

You don't have to be Tommy. But Tommy has to not be embarrassed by you.

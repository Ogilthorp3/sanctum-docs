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

## Page Structure

Every page is MDX with this skeleton:

```mdx
---
title: The Thing
description: What the thing does, in one sentence.
---

import { Aside, Card, CardGrid, Steps, Tabs, TabItem } from '@astrojs/starlight/components';

![Descriptive alt text that adds personality](../../../assets/illustrations/the-thing.png)

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

Real values. Real ports. Real paths. If you write `example.com` or `YOUR_TOKEN_HERE`, you have failed. Use the actual defaults or a realistic value from the Sanctum config.

YAML blocks for configuration. Shell blocks for commands. Annotate with comments when the config isn't self-evident, but don't narrate the obvious.

## The Haus Rule

Sanctum uses **haus** instead of "house" or "home" when referring to the dwelling. It's the brand voice — German-inflected, deliberate, and consistent. The tagline is "Your haus, wittily managed." The docs follow.

**Change to "haus":**
- "your house" → "your haus" (the dwelling running Sanctum)
- "the house" → "the haus" (when it's *this* haus)
- "home automation" → "haus automation" (the domain, Sanctum-style)
- "home intelligence" → "haus intelligence"
- "someone is home" → "someone is haus"
- "vacation house" → "vacation haus"

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

Every doc page gets one hero image. No exceptions. No SVGs. No stock photos. No clip art.

### The Style

All illustrations are **black-and-white pencil sketches** generated with **Gemini image generation** (model: `gemini-3-pro-image-preview`). The style is hand-drawn, whimsical but technically grounded, on a white background.

**Tommy the Abyssinian cat appears in every illustration** — lean, elegant, large ears, slightly smug, always observing or supervising the scene. He is the visual thread that ties the docs together.

### Generation Spec

| Property | Value |
|----------|-------|
| Model | `gemini-3-pro-image-preview` |
| Aspect ratio | `16:9` |
| Resolution | `2K` (outputs 2752x1536) |
| Format | PNG (convert from JPEG if Gemini returns JPEG — use `sips -s format png`) |
| Color | Black and white only. No color except black lines and shading. |
| Location | `src/assets/illustrations/` |

### Prompt Template

Every prompt must begin with this prefix:

```
Black and white pencil sketch illustration, wide format.
```

And end with this suffix:

```
Hand-drawn pencil style on white background. No color except black lines and shading.
```

Between them, describe the scene with:
1. **A visual metaphor** for the technical concept (conveyor belt for CI/CD, bouncer for routing, lemonade stand for pricing)
2. **Tommy** — where he is, what he's doing, his expression
3. **Labels and text** visible in the scene that ground it technically
4. **Details** that reward a closer look

### Prompt Pitfalls

- Avoid trademarked character names (Yoda, Jedi, lightsaber) — Gemini content filters will block them. Use neutral descriptions instead.
- Keep prompts under 500 characters for best results.
- If a generation fails with `PROHIBITED_CONTENT`, rephrase — don't retry the same prompt.

### Alt Text

Alt text must describe the scene **and** have personality. It's both accessibility and brand voice:

```
Good: "Tommy at the Force Flow switchboard — routing every alert in the haus through one brain"
Bad:  "Illustration of a cat near a switchboard"
```

### Consistency Checklist

Before committing a new illustration, verify:

- [ ] Black and white only (no color)
- [ ] Tommy is recognizably an Abyssinian cat (lean, large ears, elegant)
- [ ] Wide format (~16:9 aspect ratio, 2752x1536 or similar)
- [ ] White/off-white background
- [ ] Pencil sketch / hand-drawn line quality
- [ ] Metaphor is immediately readable without explanation
- [ ] Technical concept is embedded in the visual (not just decorative)
- [ ] File is real PNG (not JPEG with .png extension — use `file` to check)

### Do Not

- **No SVGs for hero images.** SVGs are for inline technical diagrams only (architecture, topology, flow). Hero images are always PNG pencil sketches.
- **No color illustrations.** The B&W pencil style is the brand.
- **No AI-generated images from other tools.** Gemini `gemini-3-pro-image-preview` only, for visual consistency.
- **No placeholder 1x1 pixel PNGs.** If the image isn't ready, leave the page without a hero until it is.

## Port Naming — The Deadpool Convention

Every service needs a port. Most infrastructure assigns them sequentially and moves on. Sanctum doesn't, because if you're going to memorize port numbers at 2 AM in your underwear, they should at least be memorable.

**The rule:** Name the ports you chose. Leave the ports that chose you.

Ports you deliberately picked — 1337, 1977, 1984, 4040, 4077, 8008, 42069 — have cultural references. They get codenames and one-liner commentary in the Port Summary table. These are creative decisions that deserve documentation.

Ports that are defaults (22, 8123) or sequential allocations (18080/18081/18085) didn't earn a story. They get dry observations about their own existence. The humor in a default port is acknowledging that it's a default. Don't force a cultural reference onto a number that's just doing its job.

**How to pick a port number for a new service:**

1. **Check if it's free.** `lsof -iTCP:<port> -sTCP:LISTEN` on Mac, `ss -tlnp` on VM. Also check `expected-ports.json` in the council-router config.
2. **Must be above 1024.** Anything below requires root to bind. LaunchAgents run as the user.
3. **Cultural reference preferred.** A year, a movie, a song, a math joke — something a human can latch onto. The port number is infrastructure _and_ documentation. When someone sees 4077 in a log, they should think "that's Force Flow" without checking a spreadsheet.
4. **No explanation required.** If the reference needs a paragraph to land, pick a different one. 1977 (Star Wars) works. 1895 (year Marconi sent the first wireless signal) does not. The test: would someone in the room get it without Googling?
5. **Update the Port Summary table.** Every new port gets a row with a Codename and Commentary. The commentary is one sentence — technically accurate, culturally aware, and exactly as amused as the situation warrants.
6. **Update `expected-ports.json`.** The council-router test suite validates that expected ports are listening. A new service that isn't in the list will trigger a Windu security alert.

**Current codenames for reference:**

| Port | Codename | Reference |
|------|----------|-----------|
| 1111 | Make-A-Wish | 11:11 |
| 1234 | Password1 | Worst password ever |
| 1337 | LEET | Hacker speak |
| 1969 | Woodstock | Music everywhere |
| 1977 | A New Hope | Star Wars |
| 1984 | Big Brother | Orwell |
| 4040 | Forty Cal | .40 caliber |
| 4077 | Hawkeye | M\*A\*S\*H |
| 5150 | Van Halen | Album / psych hold |
| 8008 | Calculator | Flip it upside down |
| 42069 | Nice. | The internet |


## Typography

Body text is justified (`text-align: justify`). This gives clean left and right edges across all documentation pages. Do not override this with centered or left-aligned prose blocks — the justified layout is a deliberate choice for readability.

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

# Missing Hero Images — Gemini Generation Prompts

Five doc pages are missing their hero illustrations. All images should match the
existing style: **black-and-white pencil sketch, hand-drawn look, wide format
(~1200x600 or ~1200x800), white/off-white background, whimsical but technically
grounded. Tommy the Abyssinian cat appears in most illustrations — lean, elegant,
slightly smug, always observing or supervising.**

Generate each with Gemini image generation. Save as PNG to
`src/assets/illustrations/`.

---

## 1. kitchen-loop.mdx → `kitchen-loop-conveyor.png`

**Prompt:**
> Black and white pencil sketch illustration, wide format. A conveyor belt
> kitchen where an Abyssinian cat (lean, elegant, slightly smug expression)
> sits on the counter supervising. The conveyor belt loops in a circle through
> six stations labeled with small signs: BACKLOG, IDEATE, TRIAGE, EXECUTE,
> POLISH, REGRESS. At each station, small robot arms or tools are working —
> one writing on a clipboard, one coding on a tiny screen, one holding a
> magnifying glass, one merging papers together. The loop feeds back into
> itself. In the background, a large specification matrix hangs on the wall
> like a restaurant menu board. Hand-drawn pencil style on white background.
> No color except black lines and shading.

**Alt text:** `Tommy supervises the Kitchen Loop — six stations, one conveyor belt, zero regressions`

---

## 2. force-flow.mdx → `force-flow-switchboard.png`

**Prompt:**
> Black and white pencil sketch illustration, wide format. A vintage telephone
> switchboard operator setup, but the operator is an Abyssinian cat (lean,
> elegant) sitting in a swivel chair with one paw on the switchboard. Cables
> connect from the left side (labeled sources: cameras, thermostats, speakers,
> agents) to the right side (labeled destinations: phone, Sonos, dashboard,
> log). A large clock on the wall shows "3:00 AM" with a sign underneath
> reading "QUIET HOURS." Some cables on the right side are disconnected
> (quiet hours filtering). One cable marked "CRITICAL" bypasses the
> switchboard entirely. Hand-drawn pencil style on white background.

**Alt text:** `Tommy at the Force Flow switchboard — routing every alert in the haus through one brain`

---

## 3. proxy.mdx → `sanctum-proxy-bouncer.png`

**Prompt:**
> Black and white pencil sketch illustration, wide format. A nightclub entrance
> scene where an Abyssinian cat in a bouncer's earpiece stands at a velvet
> rope. Behind the rope, six doors are labeled with model names (Claude,
> Gemini, Qwen, Local). A line of anthropomorphized API requests (small
> envelopes with legs) wait in queue. The cat bouncer is checking a clipboard.
> Some requests are being redirected to a side door labeled "LOCAL — Budget
> Exhausted." A small meter on the wall shows a token budget gauge. One VIP
> request walks past the rope directly to the "Claude Opus" door. Hand-drawn
> pencil style on white background.

**Alt text:** `Tommy working the door at the Sanctum Proxy — six layers of routing, one velvet rope`

---

## 4. pricing.mdx → `pricing-lemonade-stand.png`

**Prompt:**
> Black and white pencil sketch illustration, wide format. A child's lemonade
> stand, but the sign reads "SANCTUM" and the menu board shows three tiers:
> "CORE — Free (BYO Mac)", "PRO — $5/mo", "FAMILY — $12/mo". An Abyssinian
> cat sits on the counter next to a tip jar labeled "Cloud API Budget." Behind
> the stand, a Mac Mini is visible powering the whole operation with cables
> running everywhere. A small sign at the bottom reads "Your haus, your
> hardware." A customer (stick figure) looks confused at the "Free" tier.
> Hand-drawn pencil style on white background.

**Alt text:** `Tommy runs the pricing counter — your haus, your hardware, your lemonade`

---

## 5. roadmap.mdx → `roadmap-blueprint-table.png`

**Prompt:**
> Black and white pencil sketch illustration, wide format. A large architect's
> drafting table with blueprints spread out. An Abyssinian cat sits at the
> table with a pencil behind its ear, one paw on the blueprints. The
> blueprints show a haus cross-section with labeled rooms representing
> features: "Frigate NVR", "Screen Time", "Kitchen Loop." Some rooms are
> fully drawn (shipped), some are sketched in outline (planned), and some
> are just dotted lines (parked ideas). A "NOW / NEXT / LATER" sticky note
> system is pinned to a corkboard on the wall behind. Crumpled paper balls
> on the floor (rejected ideas). Hand-drawn pencil style on white background.

**Alt text:** `Tommy at the drafting table — shipped features in ink, planned features in pencil, parked ideas in the recycling bin`

---

## Consistency Checklist

After generating, verify each image against existing illustrations:

- [ ] Black and white only (no color except occasional green check / red X if relevant)
- [ ] Tommy is recognizably an Abyssinian cat (lean, large ears, elegant)
- [ ] Wide format matches existing PNGs (~2:1 or ~3:2 aspect ratio)
- [ ] White/off-white background
- [ ] Pencil sketch / hand-drawn line quality
- [ ] Metaphor is immediately readable without explanation
- [ ] Technical concept is embedded in the visual (not just decorative)

# drafts/ — finished pages waiting only on a hero image

`scripts/contrib-check.py` hard-fails any page under `src/content/docs/` without a
unique, non-SVG hero image in its first 30 lines. These drafts are complete prose,
parked here (outside the CI scan) until their image exists.

## 2026-08-11-the-archive-that-said-nothing.mdx

**Target:** `src/content/docs/operations/2026-08-11-the-archive-that-said-nothing.mdx`
**Hero:** `src/content/docs/operations/images/hero-archive-that-said-nothing.png`

Gemini image prompt, matching the house style (black-and-white pencil sketch,
hand-drawn, wide 16:9, white background, Tommy the Abyssinian observing):

> Black and white pencil sketch illustration, hand-drawn look, wide 16:9 format on
> a white background. The interior of a vast circular archive library at night —
> tall shelves of glowing data spines curving away into the dark, in the manner of
> the Jedi Archives. In the foreground, one shelf bay stands conspicuously EMPTY:
> a clean rectangular gap where volumes should be, its small brass label plate
> reading "MAIL". A librarian's high desk sits beside it with a single open ledger,
> and on the ledger's page a long column of identical handwritten entries all
> reading "0". Tommy, a lean elegant Abyssinian cat with a slightly smug
> expression, sits upright on the desk facing the empty bay, one paw resting on
> the ledger, head tilted as if unconvinced. Above the gap, a small hanging sign
> reads "NO RECORD FOUND". Warm lamplight pools on the desk; the empty bay is in
> shadow. Pencil shading only, no color.

**Alt text (keep Tommy in the alt text, not evicted into a cameo):**

> An archive that said nothing — a technical pencil sketch in the Sanctum docs
> house style, hand-drawn black-and-white, wide 16:9. The interior of a vast
> circular archive at night, shelves of data spines curving into the dark. One
> shelf bay stands empty behind a small brass plate reading MAIL, a hanging sign
> above it reading NO RECORD FOUND. On the librarian's desk beside it an open
> ledger shows a long column of identical zeroes. Tommy, the haus's force-ghost
> cat, sits on the desk facing the empty bay with one paw on the ledger, plainly
> unconvinced.

## To land it

```bash
cd ~/Projects/sanctum-docs
# 1. generate the PNG to the path above (Gemini image generation)
# 2. move the draft into place
mv drafts/2026-08-11-the-archive-that-said-nothing.mdx \
   src/content/docs/operations/
# 3. replace the placeholder hero line in the .mdx with the real
#    ![alt](./images/hero-archive-that-said-nothing.png) using the alt text above
# 4. add the sidebar entry in astro.config.mjs under Field Notes, newest first
# 5. gate it
python3 scripts/contrib-check.py && python3 scripts/story-check.py
```

Prose budget: the Chapter Rule is 1600 prose words; this draft is inside it, but
re-check after any edit — `story-check.py` reports the count.

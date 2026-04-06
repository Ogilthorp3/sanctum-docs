# Hero Roadmap

This is the controlled migration plan for Sanctum docs hero images.

The rule now is simple:

- every hero is a black-and-white pencil sketch
- every hero gets one subtle localized color halo
- `getting-started/first-run` stays untouched unless explicitly requested

The point is visual consistency without flattening the strongest compositions into technically correct wallpaper.

## Completed

- Fixed placeholder and missing hero situations
- Added a custom docs 404 page
- Refreshed flagship pages:
  - `guides/dashboard`
  - `guides/health-monitoring`
  - `architecture/living-force`
  - `architecture/agents`
- Refreshed first Mac Mini batch:
  - `getting-started/what-is-sanctum`
  - `getting-started/requirements`
  - `getting-started/installation`
  - `architecture/overview`

## Protected

- `getting-started/first-run`
  - keep `tommy-dawn-patrol.png`
  - user explicitly called this out as a favorite

## Next Batches

### Batch 2: Core Runtime

- `guides/watchdog`
- `guides/service-graph`
- `guides/skills`
- `guides/home-assistant`

Reason:

- these pages are high-visibility operational guides
- they define a lot of the site's visual mood after onboarding

### Batch 3: Core Architecture

- `architecture/proxy`
- `architecture/services`
- `architecture/config-system`
- `architecture/force-flow`

Reason:

- these are central doctrine pages
- they should feel like one system, not four illustration vintages

### Batch 4: Reference Surface

- `reference/instance-yaml`
- `reference/launchagents`
- `reference/shell-api`
- `reference/typescript-api`
- `reference/cli`

Reason:

- these are less emotionally central, but they are frequently visited
- a consistent handbook look matters here

### Batch 5: Ops Finish

- `operations/security`
- `operations/tooling`
- `operations/backup-restore`
- `operations/roadmap`
- `operations/troubleshooting`

Reason:

- these are the pages people open when things are already bad
- the art should feel deliberate, not inherited

### Batch 6: Persona Sweep

- all remaining agent profile pages except Tommy
- duplicate/shared hero decisions reviewed one by one

Reason:

- some of the strongest pages already look good
- this batch needs taste review, not bulk replacement

## Other Gaps

### 1. Homepage Voice

File:

- `src/content/docs/index.mdx`

Gap:

- strong page, but more internet-native than deadpan handbook
- should be reviewed if the target voice is closer to Valve Employee Handbook restraint

### 2. README Debt

File:

- `README.md`

Gap:

- still the default Starlight starter README
- should be replaced with actual local docs instructions

### 3. Shared Hero Review

Current shared art appears in multiple places:

- `agent-council.png`
- `implementation-audit-desk.png`
- `jocasta-archive-library.png`
- `yoda-council-chamber.png`
- `tommy-dawn-patrol-wide.png`

Gap:

- some reuse is good
- some reuse may be doing too much work and deserves dedicated replacements

### 4. Art Direction QA

For every refreshed batch:

1. regenerate
2. build locally
3. push as an isolated commit
4. verify live URLs
5. decide keep or rollback

This is the rule. No full-gallery replacements in one shot.

## Rollback Rule

Every hero batch should be committed separately so any ugly outcome can be reverted in one commit.

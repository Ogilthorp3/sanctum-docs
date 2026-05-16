# sanctum-docs

Public developer + architecture documentation for **Sanctum** at
[sanctum.run](https://sanctum.run). Sister to
[sanctum-haus](https://github.com/Ogilthorp3/sanctum-haus) (consumer
marketing at [sanctum.haus](https://sanctum.haus)).

Astro Starlight static site, deployed to Cloudflare Pages.

## What's here

| Section | Path | What it covers |
|---|---|---|
| Agents | `src/content/docs/agents/` | The 9 character-themed agent personas (Yoda, Cilghal, Mothma, Ahsoka, Jocasta, Qui-Gon, Tommy, Windu, Mundi) — their roles, backing models, and operating envelopes |
| Architecture | `src/content/docs/architecture/` | Deep-dives on every Sanctum subsystem: cathedral, council router, smart-router-cathedral, screen-time, sanctum-mlx, sanctum-gateway, sanctum-bridge, kitchen-loop, living-force, reliability-doctrine, force-flow, model-tournament, TurboQuant KV compression, secrets-trifecta, and more |
| Operations | `src/content/docs/operations/` | Field notes from real incidents and migrations |
| Getting started | `src/content/docs/getting-started/` | First-touch orientation |

Illustrations live alongside each section under `images/`.

## Dev

```sh
pnpm install
pnpm dev          # localhost:4321
pnpm build        # production build to ./dist/
pnpm preview      # preview the build locally
```

## Agent instructions

`AGENTS.md`, `CLAUDE.md`, and `GEMINI.md` are all symlinks to the same
file. Edit `AGENTS.md`; the other two follow automatically. Any LLM
working in this repo reads the same operating rules — no risk of
drift between agent personas.

## Drift detection

`.docs-drift-marker` + `scripts/` enforce that documented architecture
keeps pace with the running systems. The `com.sanctum.docs-drift-audit`
LaunchAgent (in `sanctum-runtime`) periodically reconciles claims here
against live state on `manoir` and surfaces any divergence.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) (substantial — covers editorial
voice, drift discipline, illustration sourcing, and the doc-types
taxonomy). Editorial roadmap lives in [HERO_ROADMAP.md](HERO_ROADMAP.md).

## License

Content under [CC-BY-4.0](LICENSE) (attribute to Sanctum / Bertrand
Nepveu when reusing prose or illustrations). Source code (Astro
configuration, components, scripts) under MIT — see code-file headers
where applicable.

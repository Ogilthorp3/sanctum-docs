# sanctum-docs staleness sweep — 2026-05-24

**Scope**: docs that reference RETIRED services as if they were current. Field-notes/operations are dated historical records and should usually be left as-is unless explicitly broken.

**Retirement reference**:
- **LM Studio** — retired 2026-05-11 in favor of pure-Rust `sanctum-mlx` / `sanctum-mlx-coder`. Anything describing LM Studio as a *current* inference host is stale.
- **Colima** — retired 2026-04-27 in favor of OrbStack. The `com.sanctum.openclaw.colima` LaunchAgent was retired 2026-05-16.
- **`sanctum-mlx` vs `cathedral` fork** — cathedral is now the active MLX fork (per cathedral_phase2_design memory and recent merges).
- **openclaw v2026.5.22** — current version (upgraded from 5.20 today).
- **Single proxy → 4 sanctum-server backends** — spatial, council-secure, coder, cloud.

---

## Priority 1 — Architecture docs describing current state with retired references

These are the highest priority because they're load-bearing infrastructure documentation that new contributors read first.

### 1. `src/content/docs/architecture/node-topology.mdx`
- **Stale references**: Lines 73, 115, 126, 135–146, 162, 198 — entire "Hub Network — The Bridge" section is written around `Colima (Docker)` + LM Studio. The dual-VM (QEMU + Colima) framing and the "Single Bridge Rule" explanation no longer apply because Colima was migrated to OrbStack and OrbStack uses native networking.
- **Specific gotchas**:
  - `services: [- lm_studio]` in the example `instance.yaml`
  - The whole `<Aside type="caution">` about Colima vs QEMU bridge race condition is now irrelevant
  - "Boot Sequence" section starts with `Phase 1: Docker — Colima starts...`
  - Step 5 of install: "Install a local model in LM Studio"
- **Recommendation**: **REWRITE** — replace LM Studio with `sanctum-mlx` and update the bridge/VM discussion to reflect the OrbStack migration. Preserve the historical context in an "Old Architecture (pre-2026-04)" `<Aside>` if useful.

### 2. `src/content/docs/architecture/port-summary.mdx`
- **Stale reference**: Line 36 — `| 1234 | LM Studio | Mac | Password1 | ...`
- **Recommendation**: **REWRITE** — port 1234 is now the `socat` plain-HTTP bridge to `sanctum-mlx-coder` on `:1338` (per services.mdx line 74). The "Password1" gag still works for the bridge ("plain HTTP, key under the mat"), but the service name and commentary need updating.

### 3. `src/content/docs/architecture/services.mdx`
- **Stale references**:
  - Line 110: example YAML `services: lm_studio: enabled: true, port: 1234`
  - Line 188: "VM Autostart ... re-establishes the VM-facing LM Studio bridge on 10.10.10.1:1234"
- **Recommendation**: **REWRITE** — the `lm_studio` config-example block should be removed or replaced with `mlx_coder` / `council_mlx`. The vm-autostart description should say "re-establishes the VM-facing `sanctum-mlx-coder` bridge" rather than LM Studio.
- **Note**: lines 74–75 (Coder MLX / Council MLX rows) are already accurate about the LM Studio replacement — those are good.

### 4. `src/content/docs/architecture/agents.mdx`
- **Stale reference**: Line 37 — Qui-Gon described as responsible for "Docker stability (Colima)".
- **Recommendation**: **REWRITE** (one-line edit) — change `Colima` to `OrbStack`.

### 5. `src/content/docs/architecture/overview.mdx`
- **Stale reference**: Lines 71–72 — ASCII port diagram includes `1234   LM Studio` and `1337   sanctum-mlx` (the latter is fine, but 1234 needs the same fix as port-summary).
- **Recommendation**: **REWRITE** — one-line edit.

---

## Priority 2 — Agent profile docs (highly visible to new users)

### 6. `src/content/docs/agents/yoda.mdx`
- **Stale references**: Lines 57, 64, 106, 109 — describes Yoda's local fallback as `council-mlx (LM Studio qwen/qwen3.5-35b-a3b, port 1234)`. Also "Code drops to the local Coder-14B on LM Studio".
- **Recommendation**: **REWRITE** — replace with `sanctum-mlx` (council on `:1337`) and `sanctum-mlx-coder` (`:1338`). This is one of the most-visited agent pages.

### 7. `src/content/docs/agents/ahsoka.mdx`
- **Stale references**: Lines 71, 79, 121, 147 — Ahsoka is described as running Qwen 3.5 3B 4-bit on LM Studio on the M1 satellite.
- **Recommendation**: **LEAVE-AS-HISTORICAL-RECORD** if Ahsoka is "Not deployed" (per line 96, status field). Otherwise **REWRITE** to match satellite's actual current model host (almost certainly `sanctum-mlx` too).

### 8. `src/content/docs/agents/mothma.mdx`
- **Stale reference**: Line 97 — example config `lmstudio/qwen2.5-coder-14b-instruct`.
- **Recommendation**: **REWRITE** — one-line fix to `sanctum-mlx-coder/qwen2.5-coder-14b-instruct-4bit` (or whatever the canonical model ID is now).

### 9. `src/content/docs/agents/quigon.mdx`
- **Stale reference**: Line 54 — "service doctor has a safelist. The VM process, WindowServer, and LM Studio are never killed".
- **Recommendation**: **REWRITE** — replace `LM Studio` with `sanctum-mlx` (which is in the actual safelist per Capacity Doctrine memory).

---

## Priority 3 — Operations / reference docs that describe current behavior

### 10. `src/content/docs/operations/tooling.mdx`
- **Stale reference**: Line 51 — "Mac services: Cloudflare Tunnel, Home Assistant, LM Studio, Docker".
- **Recommendation**: **REWRITE** — replace `LM Studio` with `sanctum-mlx`, replace `Docker` with `OrbStack` (since the Docker→OrbStack migration is complete).

### 11. `src/content/docs/operations/service-troubleshooting.mdx`
- **Stale reference**: Line 19 — "The LM Studio bridge listener on `10.10.10.1:1234` is gone."
- **Recommendation**: **REWRITE** — bridge target is now `sanctum-mlx-coder`, not LM Studio.

### 12. `src/content/docs/operations/backup-restore.mdx`
- **Stale references**: Lines 48, 113 — backup metadata includes "LM Studio model list"; restore step 5 is "LM Studio — Re-download models".
- **Recommendation**: **REWRITE** — replace with `sanctum-mlx` model directory (probably `~/.cache/huggingface/hub/` or wherever the MLX models live).

### 13. `src/content/docs/operations/pressure-valve.mdx`
- **Stale references**: Lines 45–47, 73 — `sanctum-mlx`, `LM Studio (helpers)`, `LM Studio node shim` all in the allowlist; line 73 mentions "you cannot freeze sshd even if a bug renames its binary to sanctum-mlx".
- **Recommendation**: **LEAVE-AS-HISTORICAL-RECORD** — this doc describes the 2026-04-19 panic and the immediate aftermath. The LM Studio entries are historically accurate. Consider adding a small "Update (2026-05-11): LM Studio retired" note rather than rewriting.

---

## Priority 4 — Field notes (dated historical records)

The 30+ operations/2026-*.mdx field notes that mention LM Studio / Colima are intentional historical records. **LEAVE AS-IS** unless an operator specifically wants to add forward-pointers (e.g., "see 2026-05-11 for the LM Studio retirement").

Notable: `operations/operational-history.mdx` is a chronological index — it should *stay* as-is, those entries describe what happened on that date.

---

## Surprises / contradictions found during sweep

1. **`mbp-reboot-runbook.mdx`** (line 128) has a note that the Mini's `:1337` is served by "a non-canonical sanctum-mlx invocation (a parallel session's Qwen3.6-35B build without TLS args)". This may already be resolved per the cathedral fork — worth a check.

2. **`architecture/eval-harness.mdx`** uses `sanctum-mlx` throughout but the cathedral fork is the active MLX fork now (per cathedral_phase2_design memory). Either the eval harness is calling the same binary just under the older name, or the doc needs to mention that `sanctum-mlx` and the cathedral fork are the same thing for routing purposes. Worth a focused read.

3. **`architecture/sanctum-mlx.mdx`** describes itself as v0.2.0 with no mention of the cathedral fork, Phase 1A/1B fusion, Phase 2 design, or the +21% throughput from the SDPA-dequant-V Metal kernel. The doc is multiple major versions behind the code. Consider a major rewrite or at least an "as-of" annotation.

4. **`architecture/services.mdx`** correctly lists Coder MLX on `:1338` and Council MLX on `:1337`, but the `services:` example YAML on line 109–125 still uses `lm_studio: port: 1234`. The doc contradicts itself within the same page.

5. The 4 sanctum-server backends (spatial, council-secure, coder, cloud) mentioned in the brief don't appear to have a dedicated architecture page. Worth checking whether `architecture/proxy.mdx` or `architecture/sanctum-cloud-proxy.mdx` already cover this, or whether a new page is needed.

6. **`operations/naming.mdx`** (line 55) already calls out "Lmstudio Proxy — Retired with the council-mlx migration" — so the retirement is partially documented in the naming doc but hasn't propagated to the docs that describe live infrastructure.

---

## Summary

- **Architecture/agent docs needing REWRITE**: 9 (priorities 1–9)
- **Operations docs needing REWRITE**: 3 (priorities 10–12)
- **LEAVE-AS-HISTORICAL-RECORD**: 1 (pressure-valve.mdx) + 30+ dated field notes
- **DELETE candidates**: 0 — every doc found is salvageable with edits

The pattern: the LM Studio retirement (2026-05-11) was well-documented in `operations/naming.mdx` but the corresponding edits to architecture, agents, and reference pages were never made. Same story for the Colima→OrbStack migration (2026-04-27).

**Next step for operator**: prioritize the 5 architecture docs first (most-visited), then the 4 agent docs (high signal-to-noise for new users), then the operations docs as time allows. Each is a 5–15 minute edit. The full set could be cleared in a focused afternoon.

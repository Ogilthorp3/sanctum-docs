#!/usr/bin/env node
/**
 * roster-sync.mjs — keep the published council roster honest.
 *
 * WHY THIS EXISTS. `refresh-roster-unified.mjs` generates
 * src/data/council-roster-unified.json from the LIVE sources of truth:
 *
 *     ~/.sanctum/sanctum-proxy/config.yaml   (the live council router)
 *     ~/.openclaw/openclaw.json              (the OpenClaw runtime seats)
 *
 * It was only ever run by hand. On 2026-08-09 the committed roster was 25 days
 * stale and the public site was stating things that were simply untrue:
 * `claude-opus-4` where the live seat is `claude-fable-5`; Mundi on OpenClaw's
 * OpenRouter where he actually runs a local Grok on :4200; and a stale tailnet
 * address published for a service that had since moved to localhost.
 *
 * Docs that hand-copy configuration ARE scattered configuration. This closes
 * the loop: the roster becomes generated output, and drift becomes a check
 * that can fail rather than a fact nobody notices.
 *
 * NOTE ON WHERE THIS CAN RUN. The two source files live on the hub, not in
 * this repo, so GitHub Actions cannot regenerate the roster — a runner has
 * neither file. This must run on the box that owns the truth (manoir), which
 * is why it commits rather than merely checking.
 *
 *   node scripts/roster-sync.mjs --check    exit 3 on drift; writes nothing.
 *                                           For a doctor probe or a pre-push.
 *   node scripts/roster-sync.mjs --write    update the file if it drifted.
 *   node scripts/roster-sync.mjs --commit   --write, then commit+push that ONE
 *                                           path. For the daily hub job.
 *   node scripts/roster-sync.mjs            same as --check.
 *
 * --commit stages a single pathspec, never `git add -A`: this repo is worked
 * by several concurrent sessions and an unrelated change must not ride along
 * on an unattended commit. It rebases with --autostash before pushing, and if
 * the push fails it says so loudly rather than leaving a silent local commit
 * that looks published but is not.
 *
 * `generated_at` is ignored when comparing. It changes on every run, so a
 * naive diff would report drift forever and commit an empty change daily —
 * the fastest way to teach everyone to ignore this job.
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = join(HERE, "..");
const COMMITTED = join(REPO, "src/data/council-roster-unified.json");
const GENERATOR = join(HERE, "refresh-roster-unified.mjs");

const mode = process.argv.includes("--commit") ? "commit"
  : process.argv.includes("--write") ? "write"
  : "check";

function git(...args) {
  return execFileSync("git", args, { cwd: REPO, encoding: "utf8" }).trim();
}

/** Everything except the timestamp — the part that is actually a fact. */
function meaningful(obj) {
  const { generated_at, ...rest } = obj;
  return JSON.stringify(rest, null, 2);
}

function readJson(path) {
  return JSON.parse(readFileSync(path, "utf8"));
}

let tmp;
try {
  tmp = mkdtempSync(join(tmpdir(), "roster-sync-"));
  const fresh = join(tmp, "roster.json");
  execFileSync(process.execPath, [GENERATOR], {
    env: { ...process.env, ROSTER_OUT: fresh },
    stdio: "pipe",
  });

  const generated = readJson(fresh);

  // Sanity floor. The generator reads live services; if the proxy config is
  // mid-edit or a source is momentarily empty it can succeed and still return
  // a truncated roster. Publishing that would silently delete seats from the
  // public site, which is worse than being a day stale. A shrinking roster is
  // a human decision, so say so and stop rather than quietly truncating.
  const MIN_AGENTS = 5;
  const count = generated?.agents?.length ?? 0;
  if (count < MIN_AGENTS) {
    console.error(
      `roster-sync: REFUSING — generator returned ${count} agents (floor is ` +
      `${MIN_AGENTS}). A source was probably empty or mid-edit. Nothing written.`);
    console.error("if the council genuinely shrank, lower MIN_AGENTS deliberately.");
    process.exit(2);
  }

  let committed;
  try {
    committed = readJson(COMMITTED);
  } catch {
    committed = null; // never generated, or unreadable — treat as full drift
  }

  if (committed && meaningful(committed) === meaningful(generated)) {
    console.log(`roster-sync: in sync (${generated.agents.length} agents)`);
    process.exit(0);
  }

  // Name what moved, so the log is useful without a diff tool.
  const byId = (r) => Object.fromEntries((r?.agents ?? []).map((a) => [a.id, a]));
  const before = byId(committed);
  const after = byId(generated);
  const changes = [];
  for (const id of new Set([...Object.keys(before), ...Object.keys(after)])) {
    const b = before[id];
    const a = after[id];
    if (!b) { changes.push(`+ ${id} (new seat)`); continue; }
    if (!a) { changes.push(`- ${id} (seat removed)`); continue; }
    if (b.api_model !== a.api_model)
      changes.push(`~ ${id}: model ${b.api_model} -> ${a.api_model}`);
    if (b.provider_label !== a.provider_label)
      changes.push(`~ ${id}: provider ${b.provider_label} -> ${a.provider_label}`);
    if ((b.api_base ?? null) !== (a.api_base ?? null))
      changes.push(`~ ${id}: endpoint ${b.api_base ?? "-"} -> ${a.api_base ?? "-"}`);
  }
  if (!changes.length) changes.push("(roles/fallbacks changed — see git diff)");

  console.log("roster-sync: DRIFT between the published roster and live config");
  for (const c of changes) console.log(`  ${c}`);

  if (mode === "check") {
    console.log("\nrun `node scripts/roster-sync.mjs --write` on the hub to update.");
    process.exit(3);
  }

  writeFileSync(COMMITTED, JSON.stringify(generated, null, 2) + "\n", "utf8");
  console.log(`\nwrote ${COMMITTED}`);

  if (mode === "commit") {
    const REL = "src/data/council-roster-unified.json";
    const body = ["chore(roster): sync published council roster to live config",
      "", "Generated by scripts/roster-sync.mjs on the hub. Changed:", "",
      ...changes.map((c) => `  ${c}`), "",
      "Sources: ~/.sanctum/sanctum-proxy/config.yaml (live council router),",
      "~/.openclaw/openclaw.json (OpenClaw runtime seats).",
    ].join("\n");
    try {
      // ONE pathspec. Concurrent sessions work this tree; nothing else rides along.
      git("commit", "-o", REL, "-m", body);
    } catch (e) {
      console.error(`roster-sync: commit failed — ${e?.message ?? e}`);
      process.exit(2);
    }
    try {
      git("pull", "--rebase", "--autostash", "-q");
      git("push", "-q");
      console.log(`roster-sync: committed and pushed ${git("rev-parse", "--short", "HEAD")}`);
    } catch (e) {
      // A local commit that never reached origin is the "looks published but
      // isn't" failure this whole file exists to prevent. Say it out loud.
      console.error(`roster-sync: COMMITTED LOCALLY BUT PUSH FAILED — ${e?.message ?? e}`);
      console.error("the site will NOT update until someone pushes this.");
      process.exit(2);
    }
  }
  process.exit(0);
} catch (err) {
  // A generator that cannot read its sources must not silently publish an
  // empty or partial roster over a good one — fail loudly and change nothing.
  console.error(`roster-sync: FAILED — ${err?.message ?? err}`);
  console.error("nothing was written; the committed roster is untouched.");
  process.exit(2);
} finally {
  if (tmp) rmSync(tmp, { recursive: true, force: true });
}

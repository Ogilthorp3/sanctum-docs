#!/usr/bin/env node
// refresh-council-roster.mjs
// ---------------------------------------------------------------------------
// Read the live agent → model assignments off the host and emit
// src/data/council-roster.json. The architecture/agents page imports
// that JSON, so refreshing the docs after a model swap is one command.
//
// Sources:
//   ~/.openclaw/openclaw.json              agent → logical model name
//   ~/.sanctum/sanctum-proxy/config.yaml   logical → provider/api_model
//
// Run: pnpm refresh:council   (or: node scripts/refresh-council-roster.mjs)
//
// CI doesn't have access to these files; the JSON is committed to git so
// each push is a snapshot of the host config at refresh time.
// ---------------------------------------------------------------------------

import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { homedir } from "node:os";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { parse as parseYaml } from "yaml";

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = join(HERE, "..", "src", "data", "council-roster.json");

const OPENCLAW = join(homedir(), ".openclaw", "openclaw.json");
const PROXY = join(homedir(), ".sanctum", "sanctum-proxy", "config.yaml");

// The five Council seats per the (Neuro)diversity is Paramount doctrine
// (2026-04-28). Display order matches the doctrine page so a side-by-side
// reader can spot drift instantly. Other openclaw.json agents (Jocasta,
// Ahsoka, …) have their own pages and are intentionally not in this
// table — the Council is the 5 seats listed below.
const ORDER = ["yoda", "mundi", "quigon", "windu", "cilghal"];
const DISPLAY_NAME = {};

function loadJson(path) {
  if (!existsSync(path)) throw new Error(`missing: ${path}`);
  return JSON.parse(readFileSync(path, "utf8"));
}
function loadYaml(path) {
  if (!existsSync(path)) throw new Error(`missing: ${path}`);
  return parseYaml(readFileSync(path, "utf8"));
}

function stripNamespace(logical) {
  // openclaw.json prefixes models like "sanctum/council-brain" or
  // "openrouter/qwen35-27b" — the prefix is a routing namespace. The
  // proxy config keys on the bare name.
  const idx = logical.indexOf("/");
  return idx >= 0 ? logical.slice(idx + 1) : logical;
}

function resolveModel(logical, proxyModels) {
  const bare = stripNamespace(logical);
  const m = proxyModels.find((x) => x.name === bare);
  if (!m) return { provider: "unknown", api_model: bare, source: logical };
  return {
    provider: m.provider,
    api_model: m.api_model,
    api_base: m.api_base ?? null,
    source: logical,
  };
}

function describeProvider(provider, api_base) {
  if (provider === "anthropic") return "Anthropic API";
  if (provider === "google" || provider === "gemini") return "Google AI Studio";
  if (provider === "openai") return "OpenAI";
  if (provider === "openrouter") return "OpenRouter";
  if (provider === "xai") return "xAI";
  if (provider === "local") {
    if (api_base?.includes(":1234")) return "LM Studio (local)";
    if (api_base?.includes(":1337")) return "sanctum-mlx (local, mTLS)";
    if (api_base?.includes(":3456")) return "Claude Max bridge (local)";
    return "Local";
  }
  return provider;
}

function main() {
  const oc = loadJson(OPENCLAW);
  const proxy = loadYaml(PROXY);
  const proxyModels = proxy.models ?? [];

  const agentsById = new Map();
  for (const a of oc.agents?.list ?? []) {
    agentsById.set(a.id, a);
  }

  const rows = [];
  for (const id of ORDER) {
    const a = agentsById.get(id);
    if (!a) continue;
    const resolved = resolveModel(a.model, proxyModels);
    rows.push({
      id,
      label: a.identity?.name ?? DISPLAY_NAME[id] ?? id,
      emoji: a.identity?.emoji ?? "",
      role: (a.identity?.theme ?? "").slice(0, 200),
      logical_model: a.model,
      provider: resolved.provider,
      provider_label: describeProvider(resolved.provider, resolved.api_base),
      api_model: resolved.api_model,
      api_base: resolved.api_base,
    });
  }

  const generatedAt = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
  const out = {
    generated_at: generatedAt,
    source: "openclaw.json + sanctum-proxy/config.yaml",
    doctrine: "/architecture/neurodiversity-doctrine/",
    agents: rows,
  };

  writeFileSync(OUT, JSON.stringify(out, null, 2) + "\n", "utf8");
  console.log(`wrote ${OUT} (${rows.length} agents, generated ${generatedAt})`);
}

main();

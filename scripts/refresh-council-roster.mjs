#!/usr/bin/env node
// refresh-council-roster.mjs
// ---------------------------------------------------------------------------
// Read the live agent → model assignments off the host and emit
// src/data/council-roster.json. The architecture/agents page imports
// that JSON, so refreshing the docs after a model swap is one command.
//
// Sources:
//   ~/.openclaw/openclaw.json              agent → {primary, fallbacks}
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

// The five Council seats per the (Neuro)diversity is Paramount doctrine.
// IDs match openclaw.json's agents.list[*].id (`main` is Yoda's seat —
// the gateway routes user-facing traffic through it). Order is doctrine
// order so a side-by-side reader can spot drift instantly.
const ORDER = ["main", "mundi", "quigon", "windu", "cilghal"];

function loadJson(path) {
  if (!existsSync(path)) throw new Error(`missing: ${path}`);
  return JSON.parse(readFileSync(path, "utf8"));
}
function loadYaml(path) {
  if (!existsSync(path)) throw new Error(`missing: ${path}`);
  return parseYaml(readFileSync(path, "utf8"));
}

function stripNamespace(logical) {
  // openclaw.json prefixes models like "council-tiered/council-max-thinking"
  // or "council-local/Qwen3.6-…" — the prefix is a routing namespace. The
  // proxy config keys on the bare model name.
  const idx = logical.indexOf("/");
  return idx >= 0 ? logical.slice(idx + 1) : logical;
}

function resolveModel(logical, proxyModels) {
  const bare = stripNamespace(logical);
  // council-local/* names refer to whatever sanctum-mlx is currently
  // serving on :1337. The bare name IS the model id (e.g.
  // "Qwen3.6-35B-A3B-4bit-text"). No proxy lookup needed.
  if (logical.startsWith("council-local/")) {
    return {
      provider: "local",
      api_model: bare,
      api_base: "https://127.0.0.1:1337",
      source: logical,
    };
  }
  const m = proxyModels.find((x) => x.name === bare);
  if (!m) return { provider: "unknown", api_model: bare, api_base: null, source: logical };
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

function modelField(agent) {
  // openclaw.json's per-agent model can be either:
  //   - the canonical {primary, fallbacks} shape (VM-aligned), or
  //   - a flat string (older Mac-only deployments).
  // Returns { primary, fallbacks } in both cases.
  const m = agent?.model;
  if (typeof m === "string") return { primary: m, fallbacks: [] };
  if (m && typeof m === "object") {
    return {
      primary: m.primary ?? "",
      fallbacks: Array.isArray(m.fallbacks) ? m.fallbacks : [],
    };
  }
  return { primary: "", fallbacks: [] };
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
    const { primary, fallbacks } = modelField(a);
    const resolved = resolveModel(primary, proxyModels);
    const fallbackResolved = fallbacks.map((f) => {
      const r = resolveModel(f, proxyModels);
      return {
        logical_model: f,
        provider: r.provider,
        provider_label: describeProvider(r.provider, r.api_base),
        api_model: r.api_model,
      };
    });
    rows.push({
      id,
      label: a.identity?.name ?? id,
      role: (a.identity?.theme ?? "").slice(0, 200),
      logical_model: primary,
      provider: resolved.provider,
      provider_label: describeProvider(resolved.provider, resolved.api_base),
      api_model: resolved.api_model,
      api_base: resolved.api_base,
      fallbacks: fallbackResolved,
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

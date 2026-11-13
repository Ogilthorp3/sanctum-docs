#!/usr/bin/env node
// refresh-council-roster.mjs
// ---------------------------------------------------------------------------
// Read the live agent → model assignments off the host / sanctum-vm and emit
// src/data/council-roster.json (the 5 routed OpenClaw seats).
// ---------------------------------------------------------------------------

import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, realpathSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { parse as parseYaml } from "yaml";

const HERE = dirname(fileURLToPath(import.meta.url));
const OUT = join(HERE, "..", "src", "data", "council-roster.json");

const OPENCLAW = join(homedir(), ".openclaw", "openclaw.json");
const PROXY = join(homedir(), ".sanctum", "sanctum-proxy", "config.yaml");

const ORDER = ["main", "mundi", "quigon", "windu", "cilghal"];
const DELIBERATION_SEAT_OVERRIDES = {
  windu: "council-tiered/council-secure",
  cilghal: "council-tiered/council-heretic",
};

function loadOpenClaw() {
  if (existsSync(OPENCLAW)) {
    return JSON.parse(readFileSync(OPENCLAW, "utf8"));
  }
  const limactl = existsSync("/opt/homebrew/bin/limactl")
    ? "/opt/homebrew/bin/limactl"
    : "limactl";
  const raw = execFileSync(
    limactl,
    ["shell", "sanctum-vm", "--", "cat", "/home/ubuntu/.openclaw/openclaw.json"],
    { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] },
  );
  return JSON.parse(raw);
}

function loadYaml(path) {
  if (!existsSync(path)) throw new Error(`missing: ${path}`);
  return parseYaml(readFileSync(path, "utf8"));
}

function stripNamespace(logical) {
  const idx = logical.indexOf("/");
  return idx >= 0 ? logical.slice(idx + 1) : logical;
}

function scanLatestCliOpus() {
  const candidates = [
    join(homedir(), ".local", "bin", "claude"),
    "/opt/homebrew/bin/claude",
    "/usr/local/bin/claude",
  ];
  for (const c of candidates) {
    try {
      if (!existsSync(c)) continue;
      const raw = readFileSync(realpathSync(c), "latin1");
      const rx = /claude-opus-(\d+)(?:-(\d{1,2}))?(?![0-9-])/g;
      let best = [0, 0, "claude-opus-5-5"];
      let m;
      while ((m = rx.exec(raw)) !== null) {
        const maj = parseInt(m[1], 10);
        const min = m[2] !== undefined ? parseInt(m[2], 10) : 0;
        if (
          maj > best[0] ||
          (maj === best[0] && min > best[1]) ||
          (maj === best[0] && min === best[1] && m[0].length > best[2].length)
        ) {
          best = [maj, min, m[0]];
        }
      }
      return best[2];
    } catch {}
  }
  return "claude-opus-5-5";
}

async function resolveBridgeModels(apiBase) {
  if (!apiBase) return new Map();
  try {
    const res = await fetch(`${apiBase.replace(/\/$/, "")}/v1/models`, {
      signal: AbortSignal.timeout(1500),
    });
    if (!res.ok) return new Map();
    const body = await res.json();
    return new Map((body?.data || []).map((x) => [x.id, x]));
  } catch {
    return new Map();
  }
}

const maxBridgeModels = await resolveBridgeModels("http://127.0.0.1:3456");

function resolveApiModel(apiModel, apiBase) {
  const bare = String(apiModel || "").trim();
  if (
    apiBase?.includes(":3456") &&
    /^(opus|claude-best-pro|claude-opus-latest|claude-opus-max)$/i.test(bare)
  ) {
    return (
      maxBridgeModels.get(bare)?.resolved_model ||
      maxBridgeModels.get("opus")?.resolved_model ||
      scanLatestCliOpus()
    );
  }
  return bare;
}

function resolveModel(logical, proxyModels) {
  const bare = stripNamespace(logical);
  const m = proxyModels.find((x) => x.name === bare);
  if (m) {
    const api_base = m.api_base ?? null;
    return {
      provider: m.provider || "local",
      api_model: resolveApiModel(m.api_model || bare, api_base),
      api_base,
      source: logical,
    };
  }
  if (logical.startsWith("council-local/")) {
    return {
      provider: "local",
      api_model: bare,
      api_base: "https://127.0.0.1:1337",
      source: logical,
    };
  }
  return { provider: "unknown", api_model: bare, api_base: null, source: logical };
}

function describeProvider(provider, api_base) {
  if (provider === "anthropic") return "Anthropic API";
  if (provider === "google" || provider === "gemini") return "Google AI Studio";
  if (provider === "openai") return "OpenAI";
  if (provider === "openrouter") return "OpenRouter";
  if (provider === "xai") return "xAI";
  if (provider === "local") {
    if (api_base?.includes(":1234")) return "sanctum-mlx-coder (local)";
    if (api_base?.includes(":1337")) return "sanctum-mlx (local, mTLS)";
    if (api_base?.includes(":3301")) return "sanctum-mlx-coder (local, mTLS)";
    if (api_base?.includes(":3456")) return "Claude Max bridge (local)";
    if (api_base?.includes(":4200")) return "Grok OAuth bridge (local)";
    if (api_base?.includes(":6543")) return "Gemini AGY bridge (local)";
    if (api_base?.includes(":6669")) return "sanctum-mlx heretic (local)";
    return "Local";
  }
  return provider;
}

function modelField(agent) {
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

const oc = loadOpenClaw();
const proxy = loadYaml(PROXY);
const proxyModels = proxy.models ?? [];

const agentsById = new Map();
for (const a of oc.agents?.list ?? []) {
  if (a?.id) agentsById.set(a.id, a);
}
for (const [id, a] of Object.entries(oc.agents?.entries ?? {})) {
  agentsById.set(id, { id, ...a });
}

const rows = [];
for (const id of ORDER) {
  const a = agentsById.get(id);
  if (!a) continue;
  const { primary: ocPrimary, fallbacks } = modelField(a);
  const primary = DELIBERATION_SEAT_OVERRIDES[id] || ocPrimary;
  const resolved = resolveModel(primary, proxyModels);
  rows.push({
    id,
    label: a.identity?.name ?? a.name ?? id,
    role: (a.identity?.theme ?? "").slice(0, 200),
    logical_model: primary,
    provider: resolved.provider,
    provider_label: describeProvider(resolved.provider, resolved.api_base),
    api_model: resolved.api_model,
    api_base: resolved.api_base,
    fallbacks: fallbacks.map((f) => {
      const rf = resolveModel(f, proxyModels);
      return {
        logical_model: f,
        provider: rf.provider,
        provider_label: describeProvider(rf.provider, rf.api_base),
        api_model: rf.api_model,
      };
    }),
  });
}

const out = {
  generated_at: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
  source: "openclaw.json + sanctum-proxy/config.yaml",
  doctrine: "/architecture/neurodiversity-doctrine/",
  agents: rows,
};

writeFileSync(OUT, JSON.stringify(out, null, 2) + "\n", "utf8");
console.log(`wrote ${OUT} (${rows.length} agents)`);

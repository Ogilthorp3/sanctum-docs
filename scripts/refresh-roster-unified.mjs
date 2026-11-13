#!/usr/bin/env node
import { execFileSync } from "node:child_process";
import { existsSync, readFileSync, realpathSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { parse as parseYaml } from "yaml";

const OUT = process.env.ROSTER_OUT || null;
const OPENCLAW = join(homedir(), ".openclaw", "openclaw.json");
const PROXY = join(homedir(), ".sanctum", "sanctum-proxy", "config.yaml");

const ORDER_RT = ["main", "mundi", "quigon", "windu", "cilghal"];

// Windu and Cilghal use perimeter/local lanes inside sanctum-vm MCP tool turns,
// while their Council deliberation chairs route through council-secure (:6543
// Gemini 4 Carbon High) and council-heretic (:6669 refusal-ablated 27B).
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
  return parseYaml(readFileSync(path, "utf8"));
}

function stripNs(logical) {
  const i = logical.indexOf("/");
  return i >= 0 ? logical.slice(i + 1) : logical;
}

function desc(p, b) {
  if (p === "anthropic") return "Anthropic API";
  if (p === "google" || p === "gemini") return "Google AI Studio";
  if (p === "openai") return "OpenAI";
  if (p === "openrouter") return "OpenRouter";
  if (p === "xai") return "xAI";
  if (p === "local") {
    if (b?.includes(":1234")) return "sanctum-mlx-coder (local)";
    if (b?.includes(":1337")) return "sanctum-mlx (local, mTLS)";
    if (b?.includes(":3301")) return "sanctum-mlx-coder (local, mTLS)";
    if (b?.includes(":3456")) return "Claude Max bridge (local)";
    if (b?.includes(":4200")) return "Grok OAuth bridge (local)";
    if (b?.includes(":6543")) return "Gemini AGY bridge (local)";
    if (b?.includes(":6669")) return "sanctum-mlx heretic (local)";
    return "Local";
  }
  return p;
}

function modelField(a) {
  const m = a?.model;
  if (typeof m === "string") return { primary: m, fallbacks: [] };
  if (m && typeof m === "object") {
    return {
      primary: m.primary || "",
      fallbacks: Array.isArray(m.fallbacks) ? m.fallbacks : [],
    };
  }
  return { primary: "", fallbacks: [] };
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

function resolveFallback(logical, proxyModels) {
  const bare = stripNs(logical);
  const m = proxyModels.find((x) => x.name === bare);
  const provider = m?.provider || "local";
  const api_base =
    m?.api_base ||
    (logical.startsWith("council-local/") ? "https://127.0.0.1:1337" : null);
  return {
    logical_model: logical,
    provider,
    provider_label: desc(provider, api_base),
    api_model: resolveApiModel(m?.api_model || bare, api_base),
  };
}

const oc = loadOpenClaw();
const proxy = loadYaml(PROXY);
const proxyModels = proxy.models ?? [];

const agentsById = new Map();
for (const a of oc.agents?.list || []) {
  if (a?.id) agentsById.set(a.id, a);
}
for (const [id, a] of Object.entries(oc.agents?.entries || {})) {
  agentsById.set(id, { id, ...a });
}

const rows = [];
for (const id of ORDER_RT) {
  const a = agentsById.get(id);
  if (!a) continue;
  const { primary: ocPrimary, fallbacks } = modelField(a);
  const primary = DELIBERATION_SEAT_OVERRIDES[id] || ocPrimary;
  const bare = stripNs(primary);
  const m = proxyModels.find((x) => x.name === bare);
  const api_base =
    m?.api_base ||
    (primary.startsWith("council-local/") ? "https://127.0.0.1:1337" : null);
  const provider = m?.provider || "local";
  rows.push({
    id,
    label: a.identity?.name || a.name || id,
    role: (a.identity?.theme ?? "").slice(0, 200),
    logical_model: primary,
    layer: "OpenClaw runtime",
    provider,
    provider_label: desc(provider, api_base),
    api_model: resolveApiModel(m?.api_model || bare, api_base),
    api_base,
    fallbacks: fallbacks.map((f) => resolveFallback(f, proxyModels)),
  });
}

// The two CLI-bench seats (Mon Mothma also has an entry in sanctum-vm openclaw.json
// pointing at council-tiered/council-brain; her technical fields resolve from the
// live proxy config + :3456 rolling `opus` alias).
const CLI_SEATS = [
  {
    id: "jocasta",
    label: "Jocasta",
    role: "Keeper of records — iMessage, Calendar, Contacts, Mail, CRM, tech-lookout; answers from what is written.",
    seat: "council-crm",
    note: "Dense 27B fine-tuned on the Memory Vault — the archivist's own mind.",
  },
  {
    id: "mothma",
    label: "Mon Mothma",
    role: "Chief of operations — deployments, runbooks, drift, backups, secret rotation; tool-armed.",
    seat: "council-brain",
  },
];

for (const s of CLI_SEATS) {
  const m = proxyModels.find((x) => x.name === s.seat);
  if (!m) {
    console.error(
      `refresh-roster: CLI seat '${s.id}' references proxy model ` +
        `'${s.seat}', which is not in the proxy config — skipping.`,
    );
    continue;
  }
  const provider = m.provider || "local";
  rows.push({
    id: s.id,
    label: s.label,
    role: s.role,
    layer: "CLI REPL",
    logical_model: s.seat,
    provider,
    provider_label: desc(provider, m.api_base),
    api_model: resolveApiModel(m.api_model || s.seat, m.api_base),
    api_base: m.api_base ?? null,
    fallbacks: [],
    ...(s.note ? { note: s.note } : {}),
  });
}

const out = {
  generated_at: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
  source: "OpenClaw runtime (5) + sanctum-cli REPL (7-seat bench)",
  doctrine: "/architecture/neurodiversity-doctrine/",
  note: "Jocasta + Mon Mothma sit on the 7-seat Council bench (Mon Mothma tracks rolling latest Opus via `opus` on :3456). The <CouncilRoster /> component renders all 7.",
  agents: rows,
};

const outPath = OUT || join(process.cwd(), "src/data/council-roster-unified.json");
writeFileSync(outPath, JSON.stringify(out, null, 2) + "\n", "utf8");
console.log("wrote", outPath, "(", rows.length, "agents)");

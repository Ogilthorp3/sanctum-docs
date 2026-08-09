#!/usr/bin/env node
import { readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { parse as parseYaml } from "yaml";

const OUT = process.env.ROSTER_OUT || null;
const OPENCLAW = join(homedir(), ".openclaw", "openclaw.json");
const PROXY = join(homedir(), ".sanctum", "sanctum-proxy", "config.yaml");

const ORDER_RT = ["main", "mundi", "quigon", "windu", "cilghal"];

function loadJson(path) { return JSON.parse(readFileSync(path, "utf8")); }
function loadYaml(path) { return parseYaml(readFileSync(path, "utf8")); }
function stripNs(logical) { const i = logical.indexOf("/"); return i>=0 ? logical.slice(i+1) : logical; }
function desc(p,b){
  if(p==="anthropic") return "Anthropic API";
  if(p==="google"||p==="gemini") return "Google AI Studio";
  if(p==="openai") return "OpenAI";
  if(p==="openrouter") return "OpenRouter";
  if(p==="xai") return "xAI";
  if(p==="local"){
    if(b?.includes(":1234")) return "sanctum-mlx-coder (local)";
    if(b?.includes(":1337")) return "sanctum-mlx (local, mTLS)";
    if(b?.includes(":3301")) return "sanctum-mlx-devstral (local, mTLS)";
    if(b?.includes(":3456")) return "Claude Max bridge (local)";
    return "Local";
  }
  return p;
}
function modelField(a){
  const m=a?.model;
  if(typeof m==="string") return {primary:m,fallbacks:[]};
  if(m&&typeof m==="object") return {primary:m.primary||"",fallbacks:Array.isArray(m.fallbacks)?m.fallbacks:[]};
  return {primary:"",fallbacks:[]};
}

const oc = loadJson(OPENCLAW);
const proxy = loadYaml(PROXY);
const proxyModels = proxy.models ?? [];
const agentsById = new Map((oc.agents?.list||[]).map(a=>[a.id,a]));

const rows = [];
for(const id of ORDER_RT){
  const a = agentsById.get(id);
  if(!a) continue;
  const {primary,fallbacks} = modelField(a);
  const bare = stripNs(primary);
  const m = proxyModels.find(x=>x.name===bare);
  const api_base = m?.api_base || (primary.startsWith("council-local/")?"https://127.0.0.1:1337":null);
  rows.push({
    id,label:a.identity?.name||id,role:(a.identity?.theme??"").slice(0,200),
    logical_model:primary,layer:"OpenClaw runtime",
    provider:m?.provider||"local",provider_label:desc(m?.provider||"local",api_base),
    api_model:m?.api_model||bare,api_base,fallbacks:fallbacks.map(f=>({logical_model:f,provider:"local",provider_label:desc("local",api_base),api_model:stripNs(f)}))
  });
}

// The two CLI-only seats. They are not in the OpenClaw runtime, so they
// cannot be discovered from openclaw.json — but their MODELS are named in the
// proxy config like everyone else's, so only identity is declared here and
// every technical field is resolved below.
//
// These used to carry hardcoded provider/api_model/api_base, and they drifted
// exactly as you would expect: Mon Mothma was published as a local MLX Qwen on
// :1337 when `council-brain` has long been Opus 5 on the Max-subscription
// bridge at :3456 — wrong provider, wrong model, wrong endpoint, invisible to
// the drift check because a constant cannot disagree with itself.
const CLI_SEATS = [
  {id:"jocasta",label:"Jocasta",
   role:"Keeper of records — iMessage, Calendar, Contacts, Mail, CRM, tech-lookout; answers from what is written.",
   seat:"council-crm",
   note:"Dense 27B fine-tuned on the Memory Vault — the archivist's own mind."},
  {id:"mothma",label:"Mon Mothma",
   role:"Chief of operations — deployments, runbooks, drift, backups, secret rotation; tool-armed.",
   seat:"council-brain"},
];

for (const s of CLI_SEATS) {
  const m = proxyModels.find(x => x.name === s.seat);
  if (!m) {
    // A seat that vanished from the proxy config is a real change, not a
    // formatting detail. Say so loudly rather than publishing a stale guess.
    console.error(`refresh-roster: CLI seat '${s.id}' references proxy model ` +
                  `'${s.seat}', which is not in the proxy config — skipping.`);
    continue;
  }
  rows.push({
    id:s.id, label:s.label, role:s.role, layer:"CLI REPL",
    logical_model:s.seat,
    provider:m.provider||"local",
    provider_label:desc(m.provider||"local", m.api_base),
    api_model:m.api_model||s.seat,
    api_base:m.api_base??null,
    fallbacks:[],
    ...(s.note?{note:s.note}:{}),
  });
}

const out={
  generated_at:new Date().toISOString().replace(/\.\d{3}Z$/,"Z"),
  source:"OpenClaw runtime (5) + sanctum-cli REPL (7-seat bench)",
  doctrine:"/architecture/neurodiversity-doctrine/",
  note:"Jocasta + Mon Mothma are CLI-only seats. The <CouncilRoster /> component now renders all 7.",
  agents:rows
};

const outPath = OUT || join(process.cwd(),"src/data/council-roster-unified.json");
writeFileSync(outPath,JSON.stringify(out,null,2)+"\n","utf8");
console.log("wrote",outPath,"(",rows.length,"agents)");

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

const cliSeats = [
  {id:"jocasta",label:"Jocasta",role:"Keeper of records — iMessage, Calendar, Contacts, Mail, CRM, tech-lookout; answers from what is written.",layer:"CLI REPL",logical_model:"council-brain",provider:"local",provider_label:"sanctum-mlx (local, mTLS)",api_model:"qwen3.6-35b-a3b-4bit",api_base:"https://127.0.0.1:1337",fallbacks:[]},
  {id:"mothma",label:"Mon Mothma",role:"Chief of operations — deployments, runbooks, drift, backups, secret rotation; tool-armed.",layer:"CLI REPL",logical_model:"council-brain",provider:"local",provider_label:"sanctum-mlx (local, mTLS)",api_model:"qwen3.6-35b-a3b-4bit",api_base:"https://127.0.0.1:1337",fallbacks:[]}
];

rows.push(...cliSeats);

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

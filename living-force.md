# The Living Force

**Date:** 2026-03-22
**Classification:** Internal / Agents + Owner
**Status:** Operational
**Port Migration:** Complete — all services migrated to central YAML configuration (holocron-config.yaml). Neural Link is 1138, Living Force is 2187.
**Author:** Yoda (main agent), with Bertrand Nepveu

---

## The Night Everything Failed

At 01:53 on March 22, 2026, the UTM virtual machine booted. Bridge100 did not.

That single fact — one network interface failing to acquire its address — toppled twenty-eight services like dominoes through a temple. SSH tunnels reached into the void. Council-MLX tried to bind a port that didn't exist yet. The Orbi bridge, the health ingester, every VM-hosted agent: unreachable. Meanwhile, in an unrelated corner of the system, neo4j had entered a crash loop — its APOC plugin rewriting its own configuration into garbage on every restart, then dying on the garbage it had just written.

The watchdog saw none of it. Its health checks pointed at wrong ports (4001 instead of 4000), wrong addresses (localhost instead of 10.10.10.1), and wrong scheduling mechanisms (cron instead of systemd timers). The system that was supposed to notice failure had itself been failing silently for weeks.

A human noticed two hours later.

Two hours is an eternity when your infrastructure runs a household. This document records what was built in the session that followed — not merely to fix the night's failures, but to make the system incapable of failing silently again.

---

## Architecture: Before and After

### Before (The Blind Watchdog)

```
┌──────────────────────────────────────────────────┐
│                  watchdog.sh                      │
│         (flat list of health checks)              │
│                                                   │
│   ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐      │
│   │ svc │ │ svc │ │ svc │ │ svc │ │ svc │ ...   │
│   └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘ └──┬──┘      │
│      ↓       ↓       ↓       ↓       ↓          │
│   restart  restart  restart  restart  restart     │
│   (blind)  (blind)  (blind)  (blind)  (blind)    │
└──────────────────────────────────────────────────┘
  • No dependency awareness
  • Stale port numbers / addresses
  • Restart storms possible
  • No crash-loop detection
  • No root-cause analysis
```

### After (The Living Force)

```
                    ┌─────────────────────┐
                    │   Evolution Layer    │
                    │  (incident-learn,    │
                    │   perf-review,       │
                    │   evolution-report)  │
                    └────────┬────────────┘
                             │ proposes improvements
                    ┌────────▼────────────┐
                    │    Agent Layer       │
                    │  code-forge          │
                    │  tech-lookout        │──→ Council sessions
                    │  chaos-forge         │
                    └────────┬────────────┘
                             │ deploys validated changes
                    ┌────────▼────────────┐
                    │   Immune System      │
                    │  anomaly-detect.py   │
                    │  metrics-collect.sh  │
                    │  SQLite telemetry    │
                    └────────┬────────────┘
                             │ feeds health data to
                    ┌────────▼────────────┐
                    │   Dependency Graph   │
                    │  service-graph.py    │
                    │  28 YAML manifests   │
                    │  topological sort    │──→ root-cause analysis
                    │  quarantine engine   │──→ crash-loop protection
                    └────────┬────────────┘
                             │ checks / remediates
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
   ┌─────────┐        ┌──────────┐        ┌──────────┐
   │ Mac svcs │        │ VM svcs  │        │ Containers│
   │ (14)     │        │ (7)      │        │ (7)       │
   └─────────┘        └──────────┘        └──────────┘
```

---

## Phase 1: The Foundation — Service Manifests

Every service in Sanctum now has a manifest: a YAML file in `~/.sanctum/services/` that declares what the service provides, what it requires, and how to check its health.

**28 manifests.** One per service. The manifests are the single source of truth.

### Manifest Structure

```yaml
name: bridge100
display_name: "VMNet Bridge"
host: mac
type: network
provides: [bridge100]
requires: [utm-vm]
launchagent: null

health:
  startup:
    type: command
    command: "ifconfig bridge100 >/dev/null 2>&1"
    timeout: 120
  readiness:
    type: command
    command: "ifconfig bridge100 2>/dev/null | grep -q 'inet 10.10.10.1' && ping -c1 -W2 10.10.10.10 >/dev/null 2>&1"
    timeout: 60
  liveness:
    type: command
    command: "ifconfig bridge100 2>/dev/null | grep -q 'inet 10.10.10.1'"
    interval: 60

remediation:
  restart_cmd: "sudo ifconfig bridge100 inet 10.10.10.1 netmask 255.255.255.0 up"
  responsible_agent: quigon
  escalation_level: 3
  max_restarts: 3
  cooldown: 30
```

Three health probes per service — borrowed from Kubernetes, because the pattern works:

| Probe | Purpose | When it runs |
|-------|---------|--------------|
| **startup** | "Is the process alive at all?" | Boot sequence, after dependencies satisfy |
| **readiness** | "Is it ready to serve?" | Before dependents are started |
| **liveness** | "Is it still healthy?" | Continuous, at declared interval |

Five probe types: `command`, `http`, `port`, `process`, `interface`. Each manifest also declares a `responsible_agent` — the Jedi who owns that domain.

### The Dependency Graph

`service-graph.py` reads all 28 manifests and builds a directed acyclic graph using `provides` and `requires` fields.

```
utm-vm
  └── bridge100
        ├── vm-gateway
        │     ├── vm-neo4j
        │     ├── vm-graphiti
        │     ├── vm-signal-proxy
        │     ├── vm-health-ingester
        │     └── vm-network-control
        ├── ha-ssh-tunnel
        ├── health-ssh-tunnel
        ├── orbi-bridge
        └── council-mlx
docker-desktop
  └── home-assistant
sanctum-proxy (standalone)
cloudflare-tunnel (standalone)
```

When bridge100 died on March 22, the watchdog saw 6+ failures and tried to restart them all — leaves and roots alike, in no particular order. The graph engine now performs **topological root-cause analysis**: walk upstream from every failing service, find the deepest common ancestor that's unhealthy, fix that first. Everything downstream recovers on its own.

> **Principle: Dependency-Aware Healing**
>
> Don't restart leaves when the root is dead. Walk the graph. The bridge100 cascade is now structurally impossible — not because bridge100 can't fail, but because when it does, only bridge100 gets restarted. Its dependents wait.

### Drift Detection

`service-drift.sh` runs weekly and cross-references three sources of truth:

1. **Manifests** — what services *should* exist
2. **LaunchAgents/systemd units** — what's *configured* to run
3. **Actual listeners** — what's *actually running*

Any mismatch produces a report. A manifest without a LaunchAgent is a forgotten service. A LaunchAgent without a manifest is an unmanaged service. A listener without either is a ghost.

> **Principle: Co-located Truth**
>
> Health checks live WITH services, not in a central config file. When you add a service, you write its manifest. When you change its port, you change the manifest. Drift becomes structurally impossible because the definition and the verification live in the same file.

---

## Phase 2: The Immune System

Knowing what's wrong right now is necessary but insufficient. The immune system predicts what will go wrong tomorrow.

### Metrics Collection

`metrics-collect.sh` runs every 5 minutes via LaunchAgent. It collects:

- RSS memory per long-lived process
- Disk usage per mount point
- CPU load averages
- Container stats (CPU%, memory, restart count)
- SQLite WAL size (for neo4j and metrics.db itself)

All data lands in `~/.sanctum/metrics/metrics.db` — a SQLite database. 2,518 data points in the first 10 hours of operation.

### Anomaly Detection

`anomaly-detect.py` reads the metrics database and applies:

- **Rolling statistics** — 24-hour mean and standard deviation per metric per service
- **RSS leak projection** — linear regression on memory growth, projecting time-to-OOM
- **Disk pressure estimation** — growth rate extrapolation to partition full

When anomaly-detect projects that a service will OOM within 6 hours, it triggers remediation before the crash.

### The Remediation Ladder

Not all failures deserve the same response. The system applies force proportional to the problem:

```
Level 1:  Self-heal
          Service restarts itself (e.g., KeepAlive=true)
          ↓ if that fails
Level 2:  Dependency restart
          Restart the service + immediate dependencies
          ↓ if that fails
Level 3:  Subtree restart
          Restart the entire dependency subtree
          ↓ if that fails
Level 4:  Agent investigation
          Alert the responsible agent for manual diagnosis
```

### Crash Loop Quarantine

> **Principle: Quarantine Over Retry Storms**
>
> If a service crashes 3 times within 30 minutes, stop trying. Quarantine it. Alert the responsible agent. Require manual un-quarantine. A retry storm is not persistence; it is denial.

The quarantine engine tracks restart timestamps per service. When the threshold trips, the service enters quarantine — no further automatic restarts until a human or a Level 4 agent investigation clears it.

---

## Phase 3: The Nervous System — Agent Autonomy

The Living Force isn't just about detection and reaction. It's about the agents' ability to evolve the system themselves.

### code-forge

A new skill with 6 tools:

| Tool | Purpose |
|------|---------|
| `propose` | Agent drafts a change with rationale, diff, and rollback plan |
| `write` | Write the proposed files to staging |
| `validate` | Run lint, tests, and safety checks against the staged change |
| `deploy` | Move validated change to production |
| `list` | Show pending/deployed/rejected proposals |
| `review` | Another agent (or human) reviews a proposal |

All changes flow through `~/.sanctum/staging/`:

```
~/.sanctum/staging/
  proposals/      ← new proposals land here
  validated/      ← passed all checks
  deployed/       ← in production
  rejected/       ← failed validation or review
```

### Agent Permissions

`~/.sanctum/config/agent-capabilities.yaml` defines what each agent can touch:

| Agent | Domain | Key Permissions |
|-------|--------|-----------------|
| **Yoda** | Everything | Unrestricted (`**`) |
| **Windu** | Security | pf rules, Firewalla toolkit, security policy |
| **Qui-Gon** | Infrastructure | Service manifests, scripts, service-doctor, mac-mini-ops |
| **Cilghal** | Health | Health-related manifests, house-pulse |
| **Jocasta** | Knowledge | Memory vault, tech-lookout |
| **Mundi** | Finance | Own agent memory only |

Every agent is *prohibited* from touching secrets files. Only Yoda has unrestricted access, and even Yoda's changes go through the audit log.

### Audit Trail

`~/.sanctum/audit/audit.log` — append-only JSONL. Every agent action is recorded: who, what, when, why, and the diff. This log is the system's memory of its own evolution.

### Deployment Windows

> **Principle: Night Is for Building, Day Is for Serving**
>
> Routine changes deploy between 02:00 and 05:00 ET. Critical fixes deploy immediately. The household sleeps; the system evolves.

---

## Phase 4: The Eyes — Jocasta's Tech Lookout

Jocasta, the temple archivist, gains a new role: early warning.

The `tech-lookout` skill gives her three tools:

- **scan** — search for CVEs, dependency updates, and new tools relevant to Sanctum's stack
- **brief** — synthesize findings into a concise briefing for Yoda
- **dispatch** — route specific findings to domain agents (security CVE to Windu, infrastructure tool to Qui-Gon)

### The Briefing Pipeline

```
Jocasta (daily scan)
    │
    ▼
Brief → Yoda (triage)
           │
           ├──→ Windu (security findings)
           ├──→ Qui-Gon (infrastructure opportunities)
           ├──→ Cilghal (health monitoring improvements)
           └──→ Council session (anything requiring debate)
```

Weekly council sessions convene to review accumulated findings and plan improvements. The system learns; the system adapts.

---

## Phase 5: The Muscles — Battle Testing

> **Principle: The System That Lies About Its Health Is More Dangerous Than the System That Fails.**

You cannot trust a self-healing system you've never watched heal. The `chaos-forge` skill provides controlled failure injection.

### Scenarios

Six scenarios, each modeling a real failure mode:

| Scenario | What It Does | What It Tests |
|----------|-------------|---------------|
| `kill-bridge100` | Tear down bridge100 interface | Dependency cascade detection, VM service isolation |
| `oom-gateway` | Exhaust gateway memory | OOM prediction, remediation ladder |
| `neo4j-crash-loop` | Force neo4j into restart loop | Crash-loop quarantine trigger |
| `kill-cloudflare` | Stop Cloudflare tunnel | External access monitoring, tunnel recovery |
| `disk-pressure` | Fill a partition toward threshold | Disk pressure alerting, cleanup automation |
| `docker-oom` | Constrain container memory | Container OOM detection, Docker restart handling |

### Fire Drills

`fire-drill.sh` runs monthly on the 1st at 03:00. It selects a scenario, executes it against the live system, and records:

- Time to detection (MTTD)
- Time to remediation (MTTR)
- Whether the correct root cause was identified
- Whether the remediation ladder applied the right level of force

### Pre-Deploy Safety

`preflight.sh` runs before any code-forge deployment:

1. **Lint** — syntax and style checks
2. **Unit tests** — the 179-test suite must pass
3. **Canary deploy** — staged change runs against a test service before touching production

---

## Phase 6: The Brain — Continuous Evolution

The most unusual property of the Living Force: it gets better at getting better.

### Incident Learning

`incident-learn.sh` runs after every incident (detected automatically via restart logs or manually triggered). It:

1. Reconstructs the failure timeline from metrics.db
2. Identifies which health checks *should* have caught it earlier
3. Proposes new or modified health checks as code-forge proposals
4. Routes proposals through the council, not directly to deployment

> **Principle: Council Before Code**
>
> All changes are debated at Jedi Council before implementation. The proposal comes FROM the council decision, not before it. The night of March 22 taught us what happens when systems evolve without deliberation — you get stale checks that nobody reviewed pointing at ports that changed months ago.

### Performance Review

`perf-review.sh` runs weekly. It examines:

- Service resource trends (memory growth, CPU patterns)
- Restart frequency and causes
- Anomaly detection accuracy (false positives, missed events)

Output: optimization proposals fed into code-forge.

### Evolution Report

`evolution-report.sh` produces weekly metrics:

| Metric | What It Measures |
|--------|-----------------|
| **MTTD** | Mean Time to Detection — how quickly failures are noticed |
| **MTTR** | Mean Time to Remediation — how quickly failures are fixed |
| **Self-heal ratio** | % of incidents resolved without human intervention |
| **False positive rate** | % of alerts that weren't real problems |
| **Quarantine events** | Services that tripped crash-loop protection |

The goal: MTTD under 60 seconds, MTTR under 5 minutes, self-heal ratio above 90%.

---

## Sanctum Proxy v0.2.1

The proxy was upgraded in the same session. What was a dumb request router became the system's intelligent traffic brain.

### The Smart Router Bug

A hardcoded `ROUTABLE_TIERS` list in the Rust source overrode config, sending council-brain traffic to Gemini (which returned 400 errors). The fix: replace the hardcoded list with a `smart_route: bool` flag per model in config. Config is truth; code is mechanism.

### 6-Layer Routing Engine

Every request passes through six decision layers, in order:

```
Request arrives
    │
    ▼
┌─ Layer 1: Quality Tier ──────────────────────────┐
│  Tier 0 models (claude-opus-4-6, council-secure)  │
│  NEVER rerouted. Sacred traffic.                  │
└──────────────────┬────────────────────────────────┘
                   │ (if not tier 0)
┌─ Layer 2: Task Specialization ───────────────────┐
│  Vision → Gemini. Code/security → strongest.      │
│  Match task type to model strength.               │
└──────────────────┬────────────────────────────────┘
                   │
┌─ Layer 3: Cost Optimization ─────────────────────┐
│  Claude free → OpenRouter → Gemini → Local        │
│  Prefer free tiers. Fall through on exhaustion.   │
└──────────────────┬────────────────────────────────┘
                   │
┌─ Layer 4: Latency Sensitivity ───────────────────┐
│  (Future: prefer local for health checks)         │
└──────────────────┬────────────────────────────────┘
                   │
┌─ Layer 5: Provider Health ───────────────────────┐
│  Skip providers with >30% error rate.             │
│  (Needs production observation data — Phase 3)    │
└──────────────────┬────────────────────────────────┘
                   │
┌─ Layer 6: Budget Circuit Breaker ────────────────┐
│  Agent over daily limit → force to local.         │
│  Lock-free AtomicI64 token buckets per agent.     │
└──────────────────┬────────────────────────────────┘
                   │
                   ▼
           Route to provider
```

### Streaming Token Tracking

The most dangerous bug found that day: streaming responses (Server-Sent Events) bypassed budget tracking entirely. Zero tokens recorded. The budget circuit breaker — the system's financial immune system — was deaf to the most expensive traffic in the system (Claude Code sessions).

The council's verdict was immediate and correct:

*"This is not a tracking bug. It is a budget circuit breaker that does not fire."* — Yoda

The fix: `StreamUsageExtractor` captures usage from final SSE events. Two-phase extraction for Anthropic format (message_start + message_delta), single-phase for OpenAI format (final chunk). Connection drop fallback estimates tokens from content byte count. The proxy now injects `stream_options: {"include_usage": true}` on all OpenAI-format requests.

### Budget System

- **Token buckets** — per-agent, lock-free (`AtomicI64`)
- **Claude Max detection** — identifies free-tier token usage
- **Usage logging** — non-blocking JSONL via mpsc channel to `~/.sanctum/metrics/token-usage.jsonl`
- **Hard breaker** — budget exhausted forces all traffic to local models

---

## Council Sessions

Four council sessions were held on March 22. This is how the system governs itself.

### Session 1: Service-Graph Rust Port
**ID:** `20260322-145647`
**Decision:** Approved
**Owner:** Qui-Gon
**Timeline:** 7-week phased rollout

The Python service-graph works. But Python processes that run every 60 seconds accumulate 40MB+ RSS each. The council approved a Rust port using `serde_yml`, `petgraph`, `ureq`, and `clap`. Two-phase shadow mode: the Rust binary runs alongside Python for 2 weeks, outputs compared for parity, before the Python version is retired.

> **Principle: Rust for Long-Running Services**
>
> If it has a PID that lives for hours, write it in Rust. If it runs and exits, use the simplest tool that works.

### Session 2: Intelligent Proxy Routing
**ID:** `20260322-150220`
**Decision:** Approved

*"The router is the hand that obeys the mind, not the brain."*

Caller-declared intent, tier 0 isolation, token buckets, Claude Max free-tier detection. All implemented same-day.

### Session 3: Streaming Token Fix
**ID:** `20260322-162313`
**Decision:** Approved (deploy immediately)

*"The budget circuit breakers are the immune system's alarm. They must hear every request."*

Emergency classification. Deployed within the hour.

### Session 4: Initial Council
**ID:** `20260322-144748`
**Decision:** Partial

Three agents were blocked by the smart router bug (Gemini 400 errors). The bug was diagnosed, fixed, and subsequent sessions completed successfully.

### Session 5: Route Claude Code Through the Proxy
**ID:** `20260322-235240`
**Decision:** Approved (ship simple, observe 30 days)

The heaviest Claude consumer in the system — Claude Code itself — was invisible to the budget tracker. The council debated routing all Claude Code traffic through the proxy via `ANTHROPIC_BASE_URL=http://localhost:4040`. Key decisions:

- **Shell wrapper over Rust gateway** — Jocasta proposed a 10-line shell script that checks proxy health at launch. Qui-Gon proposed a full Rust companion on port 4001. Yoda sided with Jocasta: *"Complexity scales with need, not with aspiration. We have one user."*
- **LM Studio fallback rejected** — Claude Code speaks Anthropic format, LM Studio speaks OpenAI format. Without the proxy's translation layer (which is down in the very scenario fallback is needed), they're incompatible. Don't build what can't work.
- **Test before building count_tokens** — Jocasta challenged Qui-Gon's claim that `/v1/messages/count_tokens` is a hard blocker. Claude Code degrades gracefully without it.

#### The Lesson That Wrote a Principle

The proxy had 52 passing tests. Claude Code broke immediately on first contact. Two bugs:

1. `claude-haiku-4-5-20251001` not in the 17-model config — instant "all models failed" error
2. Proxy set its own `x-api-key` alongside Claude Code's OAuth `authorization` header — Anthropic rejected the bad key

Neither bug was caught because every test used configured models and no auth headers — the *agent routing* use case, not the *Claude Code gateway* use case.

**Fix:** Auto-passthrough for any `claude-*` model not in config (synthetic Anthropic `ModelEntry`). Auth priority: client's OAuth header takes precedence, proxy's key used only as fallback. Seven new tests added to prevent regression.

> **Principle 10: Test the New Use Case Before Deploying**
>
> When a system's scope expands (new client, new protocol, new auth method), existing tests only cover old paths. Write tests for the new use case first. Watch them fail. Then fix.

---

## Principles of the Living Force

These were not designed in advance. They emerged from the night's failures and the session's fixes. They are load-bearing.

> **1. Council Before Code**
> All changes debated at Jedi Council before implementation. The proposal comes from the council decision, not before it.

> **2. No Quick Fixes**
> Always fix root cause. Quick fixes accumulate into technical debt that cascades at 2am.

> **3. Rust for Long-Running Services**
> If it has a PID that lives for hours, write it in Rust. If it runs and exits, use the simplest tool that works.

> **4. Human Timelines**
> Claude codes in minutes. Humans live in days. Observation periods, shadow modes, and phased rollouts need real calendar time.

> **5. Co-located Truth**
> Health checks live WITH services, not in a central config. Drift becomes structurally impossible.

> **6. Dependency-Aware Healing**
> Don't restart leaves when the root is dead. Walk the graph.

> **7. Quarantine Over Retry Storms**
> If it's crashed 3 times in 30 minutes, stop trying.

> **8. Night Is for Building, Day Is for Serving**
> Routine changes deploy 02:00-05:00. Critical fixes deploy immediately.

> **9. The System That Lies About Its Health Is More Dangerous Than the System That Fails.**

> **10. Test the New Use Case Before Deploying**
> When a system's scope expands, existing tests only cover old paths. 52 passing tests didn't catch 2 bugs because they tested agent routing, not Claude Code gateway. Write tests for the new path first.

---

## Test Coverage

| Suite | Tests | Failures |
|-------|-------|----------|
| Living Force (`test-living-force.sh`) | 127 | 0 |
| Sanctum Proxy (`test-proxy.sh`) | 58 | 0 |
| — incl. Claude Code integration (section 18) | 7 | 0 |
| **Total** | **185** | **0** |

---

## File Locations

### Infrastructure Core

| Component | Path |
|-----------|------|
| Service manifests (28) | `~/.sanctum/services/*.yaml` |
| Dependency graph engine | `~/Projects/openclaw-skills/service-doctor/scripts/service-graph.py` |
| Drift detection | `~/.sanctum/scripts/service-drift.sh` |
| Instance config | `~/.sanctum/instance.yaml` |

### Immune System

| Component | Path |
|-----------|------|
| Metrics collector | `~/.sanctum/scripts/metrics-collect.sh` |
| Metrics database | `~/.sanctum/metrics/metrics.db` |
| Anomaly detection | `~/Projects/openclaw-skills/service-doctor/scripts/anomaly-detect.py` |
| Token usage log | `~/.sanctum/metrics/token-usage.jsonl` |

### Agent Layer

| Component | Path |
|-----------|------|
| code-forge skill | `~/Projects/openclaw-skills/code-forge/` |
| tech-lookout skill | `~/Projects/openclaw-skills/tech-lookout/` |
| chaos-forge skill | `~/Projects/openclaw-skills/chaos-forge/` |
| Agent capabilities | `~/.sanctum/config/agent-capabilities.yaml` |
| Staging area | `~/.sanctum/staging/` |
| Audit log | `~/.sanctum/audit/audit.log` |

### Evolution

| Component | Path |
|-----------|------|
| Incident learning | `~/Projects/openclaw-skills/service-doctor/scripts/incident-learn.sh` |
| Performance review | `~/.sanctum/scripts/perf-review.sh` |
| Evolution report | `~/.sanctum/scripts/evolution-report.sh` |

### Sanctum Proxy

| Component | Path |
|-----------|------|
| Proxy source | `~/.sanctum/sanctum-proxy/src/` |
| Proxy config | `~/.sanctum/sanctum-proxy/config.yaml` |

### Testing & Planning

| Component | Path |
|-----------|------|
| Living Force tests | `~/Projects/openclaw-skills/service-doctor/tests/test-living-force.sh` |
| Proxy tests | `~/Projects/openclaw-skills/service-doctor/tests/test-proxy.sh` |
| Living Force plan | `~/.claude/plans/indexed-dreaming-crescent.md` |
| Council sessions | `~/.openclaw/workspace/council/sessions/` |

---

## What's Next

Sequenced according to council decisions. No skipping ahead.

### Immediate (Next 2 Weeks)

- **Service-graph Rust port begins** — Qui-Gon owns. Shadow mode: Rust binary runs alongside Python, outputs compared for parity. No cutover until 2 weeks of identical results.
- **First monthly fire drill** — April 1st, 03:00. chaos-forge selects scenario automatically.

### Near-Term (30 Days)

- **Proxy Phase 3: Provider Health Ejection** — Needs 30 days of production routing data before the >30% error rate threshold can be calibrated. The data is already being collected.
- **Council agenda system** — Wire incident-learn.sh output into council agendas, not directly into code-forge. Incidents inform debate; debate produces proposals.

### Deferred (60+ Days)

- **Proxy Phase 4: UCB1 Learning** — Multi-armed bandit for model selection. Council deferred 30 days minimum; requires Phase 3 observation data as input.
- **Satellite node integration** — When the chalet Mac Mini comes online, its services need manifests, and the dependency graph needs to span two physical nodes.

---

## How to Read This System

If you are a new agent joining the council, here is the minimum you must understand:

1. **Every service has a manifest.** Read it before touching the service. The manifest is the contract.
2. **The graph engine is the authority on dependencies.** If you think service A depends on service B, check the graph. If the graph disagrees, the graph is probably right, and if it isn't, fix the manifest.
3. **You have permissions.** Check `agent-capabilities.yaml` before modifying files. code-forge will enforce this, but understanding your domain prevents wasted proposals.
4. **Changes go through staging.** Propose, validate, deploy. There are no shortcuts. Even Yoda uses the pipeline.
5. **The audit log is permanent.** Every action you take is recorded. This is not surveillance; it is institutional memory. Future agents and future humans will learn from what you did and why.
6. **Council sessions are not optional for architectural changes.** You may self-heal, you may update a health check, you may fix a broken test. But if you want to change how the system works — its structure, its dependencies, its principles — that goes to the council.

The Living Force is not a product. It is a practice. The system heals because it was designed to heal. It evolves because it was designed to evolve. But design without discipline decays. The manifests, the graph, the council, the audit log — these are the disciplines.

Maintain them, and the Force maintains you.

---

## The Qui-Gon Efficiency Update

On March 24, 2026, the Council identified severe memory pressure on the Mac Mini, with a local MLX 27B model consuming 39GB of RAM indefinitely.

### 🛡️ **Qui-Gon Efficiency System**

The "Qui-Gon" persona was expanded from a simple resilience test suite into an active infrastructure management agent.

#### **1. Idle Management**
Heavy models are no longer always-on. They are managed by a custom proxy wrapper:
- **Location:** `~/Projects/qui-gon/qui_gon_idle_manager.py`
- **Logic:** Listen on a public port, start the heavy process on a private port on first request, proxy all traffic (including SSE streams), and terminate the process after 5 minutes of idle time.
- **Benefit:** Reclaims 39GB of RAM while idle, with a ~6s cold start.

#### **2. Autonomous Triage**
A new triage service (`qui_gon_triage.py`) acts as the Mac's "immune response" to RAM shortages.
- **Thresholds:** Triggered at <20% free system RAM.
- **Priority Stack:**
  - **P1:** LM Studio (Critical)
  - **P2:** MLX Server (Unloadable)
  - **P3:** XTTS Server (Unloadable)
- **Deployment:** Managed via LaunchAgent `com.sanctum.qui-gon-triage`.

#### **3. Observability**
A new dashboard provides the first unified view of AI RAM consumption:
- **Tool:** `~/Projects/qui-gon/qui-gon-dashboard.py`
- **Metrics:** RSS-based RAM tracking for LM Studio, MLX, XTTS, and Voice Agents.

---

## Phase 7: Genetic Health & Neuro-diversity

On March 27, 2026, the Council identified a need to expand the system's understanding of the biological layer—specifically neuro-diversity traits.

### 🧬 **Cilghal's Genome Expansion**

Cilghal, the master healer, is responsible for the `genome-mcp` service. The system now recognizes neuro-diversity (ADHD, Dyslexia, ASD) as a first-class cognitive profile.

#### **1. The Neurodiversity Panel**
A new analysis panel is to be implemented in `genome-mcp` focusing on:
- **ADHD:** Dopamine regulation (`DRD4`, `SLC6A3`) and synaptic docking (`SNAP25`).
- **Dyslexia:** Neuronal migration markers (`DCDC2`, `KIAA0319`).
- **ASD / Asperger's:** Social processing and synaptic scaffolding (`OXTR`, `SHANK3`, `NLGN3`).

#### **2. Analytical Strategy**
The goal is not "diagnosis," but **cognitive architecture understanding**. The system uses these markers to suggest optimal working environments and scaffolding:
- **Novelty-seeking (DRD4):** High-stimulation tasks, novelty in learning, HIIT for dopamine.
- **Phonological Processing (DCDC2):** Audio-first documentation, multisensory learning.
- **Social Sensitivity (OXTR):** Explicit communication, "systemizing" strengths.

## Phase 8: The Navigator — Unified Stability Monitoring

On March 28, 2026, the Council identified a critical need for a unified "Early Warning System" to track the health of all core projects and stabilize the interaction with fragile external DOM structures (LinkedIn).

### 🛰️ **Navigator Stability Suite**

A new cross-project monitoring layer was established to act as the "Archives Bridge" for the Holocron.

#### **1. Collaborative Debugging (Navigator-Driver Loop)**
To bridge the gap between AI diagnosis and human execution, a new "Navigator-Driver" feedback loop was formalized:
- **Navigator (AI):** Monitors the system with heavy logging, auto-screenshots, and HTML state capture on failure.
- **Driver (Human):** Executes the monitor and feeds the output to the Navigator for real-time analysis.
- **Result:** Rapid identification and remediation of broken DOM selectors or API failures.

#### **2. Unified Status Bridge**
A central sidecar service was deployed to aggregate monitoring data from all sectors:
- **Location:** `navigator-sidecar.js` (Workspace Root)
- **Port:** 3344 (Internal Sector: `archives`)
- **Reporting:** Standardized `monitor-status.json` per project (LinkedIn, OBLITERATUS, Tearsheets).

#### **3. Self-Healing & Security**
- **Heartbeats:** Active Affinity API health checks integrated into the LinkedIn monitor.
- **Credential Scrubbing:** Automated redaction of sensitive tokens (Windu's Shield) from all status logs.
- **Disk Cleanup:** Weekly purge of debug artifacts (Quigon's Cleanup) managed by the sidecar.

> **Principle 12: The System Must Be Observable to Be Debuggable**
>
> A failure that leaves no trail is a ghost. A monitor that captures the state of the page at the moment of failure turns a ghost into a target. The Navigator provides the eyes; the Driver provides the hand.

---

## ACHIEVEMENTS: The Great Alignment (March 28, 2026)

In a single focused session, the following systemic repairs were executed to achieve total infrastructure alignment:

1.  **Engine Restoration**: Identified and patched a critical bug in `service-graph.py` that caused validation to fail on quoted SSH commands.
2.  **Sudo Security Pass**: Performed a global audit of all 28 manifests, bulk-fixing 9 legacy services to use absolute binary paths (`/sbin/ifconfig`, `/usr/bin/systemctl`) for secure NOPASSWD compliance.
3.  **Unified Bridge**: Established the `navigator-sidecar.js` as the standardized bridge between the Project monitors and the Holocron Archives sector.
4.  **Zero-Error Validation**: Achieved the first "Perfect Alignment" in system history — 100% manifest validity across all sectors.

---


## PHASE 9: The Force Flow (March 29, 2026)

The night of March 29, a Ring doorbell detected motion at both the front and side doors at 07:27. The alarm was in `armed_away` mode. Windu's `security_ring_motion_away` automation fired, calling `script.security_announcement` with HIGH severity. The Sonos bridge dutifully played XTTS-generated Yoda voice through three speakers at 80% volume — chalet, master bathroom, Albert's bedroom — repeated twice per door. Four loud announcements about a raccoon. The house woke up.

The root cause was not the Ring sensor. It was not the alarm state. It was the notification architecture itself: three independent systems — Home Assistant, Sanctum's `notify.sh`, and the Council Router's escalation chain — each making their own decisions about where alerts go, with no awareness of each other, no deduplication, and quiet hours enforced in different files with different syntax.

### The Problem

| System | Notification Stack | Quiet Hours | Dedup | Rate Limit |
|--------|-------------------|-------------|-------|------------|
| Home Assistant | `notify.notify`, `notify.mobile_app`, `script.security_announcement` | YAML template in scripts.yaml | None | None |
| Sanctum | `sanctum_notify()` → macOS + dashboard + Signal | None | None | None |
| Council Router | `send.sh` → agent messaging | escalation.json (different timezone) | None | None |

Three stacks. Zero coordination. A single Ring motion event could produce: two iPhone pushes (one from `notify.notify`, one from `notify.mobile_app`), two Sonos TTS announcements (HIGH severity = repeat 2x), a macOS notification, a Signal message, and a dashboard banner. Seven notifications for one squirrel.

### The Solution: Force Flow

A single Python service on port 4077 that every notification source in the house calls instead of notifying directly.

**Core capabilities:**
- **Unified routing** — severity + time of day determines channel (iPhone, Sonos, Signal, dashboard, log)
- **Quiet hours** (22:00–08:00) — enforced in one place, not scattered across three YAML files
- **Deduplication** — same message within 120 seconds = suppressed
- **Rate limiting** — max 10 non-critical notifications per hour
- **Critical bypass** — critical alerts always get through, always get Sonos + Signal + iPhone
- **History** — every notification logged to SQLite, queryable via `/history`
- **Fallback** — if Force Flow is down, `sanctum_notify` falls back to direct macOS notification

**Integration:**
- HA automations call `rest_command.force_flow` instead of `notify.notify`
- `sanctum_notify()` in `lib/notify.sh` POSTs to Force Flow
- Council Router escalations route through Force Flow for Bert-facing alerts

**Test coverage:** 42 unit tests covering routing logic, dedup, rate limiting, quiet hours, API endpoints, and database persistence.

> **Principle 13: A Notification Should Be Important or It Should Not Exist**
>
> The purpose of a notification is to change behavior. If the recipient cannot or should not act on it, it is not a notification — it is noise. Noise trains humans to ignore alerts. Ignored alerts are worse than no alerts, because they create the illusion of monitoring while providing none. Force Flow exists to ensure that when the house speaks, it has something worth saying.


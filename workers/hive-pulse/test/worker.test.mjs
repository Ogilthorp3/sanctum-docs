import test from "node:test";
import assert from "node:assert/strict";
import worker, {
  handleAnalytics,
  handleDeletePulse,
  handleInstallEvent,
  handleLatestJson,
  handlePulse,
  handleVerifySeal,
} from "../src/index.js";

/**
 * Minimal in-memory D1 mock supporting the exact SQL statements in src/index.js.
 */
function createMockDb() {
  const nodes = new Map();
  const versionChecks = new Map();
  const installFunnel = new Map();

  return {
    _nodes: nodes,
    _versionChecks: versionChecks,
    _installFunnel: installFunnel,
    prepare(sql) {
      let args = [];
      const stmt = {
        bind(...params) {
          args = params;
          return stmt;
        },
        async run() {
          if (sql.includes("INSERT INTO nodes")) {
            const [
              node_id,
              seat_number,
              claim_code,
              first_seen_date,
              first_seen_at,
              last_seen_at,
              onboard_completed,
              chip,
              memory_gb,
              os_version,
              country,
              cli_version,
              modules_json,
            ] = args;
            const existing = nodes.get(node_id);
            if (!existing) {
              nodes.set(node_id, {
                node_id,
                seat_number,
                claim_code,
                first_seen_date,
                first_seen_at,
                last_seen_at,
                onboard_completed,
                chip,
                memory_gb,
                os_version,
                country,
                cli_version,
                modules_json,
                pulse_count: 1,
              });
            } else {
              existing.claim_code = existing.claim_code || claim_code;
              existing.last_seen_at = last_seen_at;
              existing.onboard_completed = Math.max(existing.onboard_completed, onboard_completed);
              if (chip !== "Unknown") existing.chip = chip;
              if (memory_gb > 0) existing.memory_gb = memory_gb;
              if (os_version !== "Unknown") existing.os_version = os_version;
              if (country !== "ZZ") existing.country = country;
              if (cli_version !== "unknown") existing.cli_version = cli_version;
              if (modules_json !== "[]") existing.modules_json = modules_json;
              existing.pulse_count += 1;
            }
            return { success: true, meta: { changes: 1 } };
          }
          if (sql.startsWith("DELETE FROM nodes")) {
            const existed = nodes.delete(args[0]);
            return { success: true, meta: { changes: existed ? 1 : 0 } };
          }
          if (sql.includes("INSERT INTO daily_version_checks")) {
            const [date, cli_version, os_family] = args;
            const k = `${date}|${cli_version}|${os_family}`;
            versionChecks.set(k, (versionChecks.get(k) || 0) + 1);
            return { success: true, meta: { changes: 1 } };
          }
          if (sql.includes("INSERT INTO install_funnel")) {
            const [date, step, cli_version, os_major, country] = args;
            const k = `${date}|${step}|${cli_version}|${os_major}|${country}`;
            installFunnel.set(k, (installFunnel.get(k) || 0) + 1);
            return { success: true, meta: { changes: 1 } };
          }
          throw new Error(`Unhandled run SQL: ${sql}`);
        },
        async first() {
          if (sql.includes("WHERE node_id = ?")) {
            return nodes.get(args[0]) || null;
          }
          if (sql.includes("MAX(seat_number)")) {
            let maxSeat = 0;
            for (const n of nodes.values()) {
              if (typeof n.seat_number === "number" && n.seat_number > maxSeat) {
                maxSeat = n.seat_number;
              }
            }
            return { max_seat: maxSeat };
          }
          if (sql.includes("WHERE claim_code = ?")) {
            for (const n of nodes.values()) {
              if (n.claim_code === args[0]) return n;
            }
            return null;
          }
          if (sql.includes("AS active_7d") && !sql.includes("AS active_24h")) {
            const [cutoff7d] = args;
            let active = 0;
            for (const n of nodes.values()) {
              if (n.last_seen_at >= cutoff7d) active += 1;
            }
            return { total_nodes: nodes.size, active_7d: active };
          }
          if (sql.includes("AS active_24h")) {
            const [c24, c7, c30] = args;
            let onboard = 0, a24 = 0, a7 = 0, a30 = 0, ram = 0;
            let earliest = null;
            for (const n of nodes.values()) {
              if (n.onboard_completed === 1) onboard += 1;
              if (n.last_seen_at >= c24) a24 += 1;
              if (n.last_seen_at >= c7) a7 += 1;
              if (n.last_seen_at >= c30) a30 += 1;
              ram += n.memory_gb;
              if (!earliest || n.first_seen_date < earliest) earliest = n.first_seen_date;
            }
            return {
              total_nodes: nodes.size,
              onboard_completed: onboard,
              active_24h: a24,
              active_7d: a7,
              active_30d: a30,
              total_ram_gb: ram,
              seed_zero_since: earliest,
            };
          }
          throw new Error(`Unhandled first SQL: ${sql}`);
        },
        async all() {
          if (sql.includes("WHERE seat_number IS NOT NULL")) {
            const rows = [...nodes.values()]
              .filter((n) => n.seat_number !== null && n.seat_number !== undefined && n.seat_number <= 10)
              .sort((a, b) => a.seat_number - b.seat_number);
            return { results: rows };
          }
          if (sql.includes("GROUP BY chip")) {
            const m = new Map();
            for (const n of nodes.values()) m.set(n.chip, (m.get(n.chip) || 0) + 1);
            return { results: [...m.entries()].map(([chip, cnt]) => ({ chip, cnt })) };
          }
          if (sql.includes("GROUP BY country")) {
            const m = new Map();
            for (const n of nodes.values()) m.set(n.country, (m.get(n.country) || 0) + 1);
            return { results: [...m.entries()].map(([country, cnt]) => ({ country, cnt })) };
          }
          if (sql.includes("GROUP BY cli_version")) {
            const m = new Map();
            for (const n of nodes.values()) m.set(n.cli_version, (m.get(n.cli_version) || 0) + 1);
            return { results: [...m.entries()].map(([cli_version, cnt]) => ({ cli_version, cnt })) };
          }
          if (sql.includes("SELECT modules_json FROM nodes")) {
            return { results: [...nodes.values()].map((n) => ({ modules_json: n.modules_json })) };
          }
          if (sql.includes("GROUP BY first_seen_date")) {
            const [since] = args;
            const m = new Map();
            for (const n of nodes.values()) {
              if (n.first_seen_date < since) continue;
              const cur = m.get(n.first_seen_date) || { date: n.first_seen_date, new_nodes: 0, onboarded: 0 };
              cur.new_nodes += 1;
              if (n.onboard_completed === 1) cur.onboarded += 1;
              m.set(n.first_seen_date, cur);
            }
            return { results: [...m.values()].sort((a, b) => a.date.localeCompare(b.date)) };
          }
          if (sql.includes("FROM daily_version_checks")) {
            const [since] = args;
            const m = new Map();
            for (const [k, cnt] of versionChecks.entries()) {
              const date = k.split("|")[0];
              if (date < since) continue;
              m.set(date, (m.get(date) || 0) + cnt);
            }
            return {
              results: [...m.entries()]
                .sort((a, b) => a[0].localeCompare(b[0]))
                .map(([date, checks]) => ({ date, checks })),
            };
          }
          if (sql.includes("FROM install_funnel")) {
            const [since] = args;
            const results = [];
            for (const [k, count] of installFunnel.entries()) {
              const [date, step, cli_version, os_major, country] = k.split("|");
              if (date < since) continue;
              results.push({ date, step, cli_version, os_major, country, count });
            }
            results.sort((a, b) => a.date.localeCompare(b.date));
            return { results };
          }
          throw new Error(`Unhandled all SQL: ${sql}`);
        },
      };
      return stmt;
    },
  };
}

test("health endpoint reports zero_pii, verify-seal, and install-event", async () => {
  const res = await worker.fetch(new Request("https://hive.sanctum.run/health"), { DB: createMockDb() });
  assert.equal(res.status, 200);
  const data = await res.json();
  assert.equal(data.ok, true);
  assert.equal(data.zero_pii, true);
  assert.equal(data.endpoints.includes("/verify-seal?code=..."), true);
  assert.equal(data.endpoints.includes("POST /install-event"), true);
});

test("pulse mints Seed #1 + Founding Circle #2 seals, verifies offline, and deletes cleanly", async () => {
  const db = createMockDb();
  const env = { DB: db, SEAL_SECRET: "test-sovereign-secret-key" };
  const t0 = Date.parse("2026-11-26T15:00:00Z");

  // Seed #0 Founder node pre-existing in DB (seat_number = 0)
  db._nodes.set("00000000000000000000000000000001", {
    node_id: "00000000000000000000000000000001",
    seat_number: 0,
    claim_code: null,
    first_seen_date: "2026-11-22",
    first_seen_at: "2026-11-22T12:00:00.000Z",
    last_seen_at: "2026-11-26T15:00:00.000Z",
    onboard_completed: 1,
    chip: "Apple M4 Pro",
    memory_gb: 64,
    os_version: "macOS 27.2.1",
    country: "CA",
    cli_version: "1.0.5",
    modules_json: '["mlx","proxyd"]',
    pulse_count: 5,
  });

  // Bad node_id rejected
  const bad = await handlePulse(
    new Request("https://hive.sanctum.run/pulse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ node_id: "not-hex!" }),
    }),
    env,
    t0
  );
  assert.equal(bad.status, 400);

  // First outsider Mac joins -> mints Seed #1!
  const nodeA = "a1b2c3d4e5f60718293a4b5c6d7e8f90";
  const ok1 = await handlePulse(
    new Request("https://hive.sanctum.run/pulse", {
      method: "POST",
      headers: { "Content-Type": "application/json", "CF-Connecting-IP": "1.2.3.4" },
      body: JSON.stringify({
        node_id: nodeA,
        event: "onboard",
        chip: "Apple M4 Max",
        memory_gb: 128,
        os_version: "macOS 26.1",
        country: "fr",
        cli_version: "v1.0.5",
        modules: ["backup", "link", "INVALID!"],
      }),
    }),
    env,
    t0
  );
  assert.equal(ok1.status, 200);
  const j1 = await ok1.json();
  assert.equal(j1.hive_nodes, 2);
  assert.equal(j1.newly_minted, true);
  assert.equal(j1.seal.seat_number, 1);
  assert.equal(j1.seal.tier, "seed-1");
  assert.equal(j1.seal.title, "Seed #1 — First Beyond the Walls");
  assert.match(j1.seal.claim_code, /^SEED1-[A-F0-9]{4}-[A-F0-9]{4}$/);
  assert.equal(j1.seal.signature.length, 64);

  // Verify zero IP stored anywhere
  const stored = db._nodes.get(nodeA);
  assert.equal(stored.country, "FR");
  assert.equal(stored.cli_version, "1.0.5");
  assert.equal(stored.onboard_completed, 1);
  assert.equal(stored.modules_json, '["backup","link"]');
  assert.equal(JSON.stringify(stored).includes("1.2.3.4"), false);

  // Second heartbeat keeps exact same Seed #1 seat & claim code!
  const ok2 = await handlePulse(
    new Request("https://hive.sanctum.run/pulse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ node_id: nodeA, event: "heartbeat" }),
    }),
    env,
    t0 + 3600_000
  );
  assert.equal(ok2.status, 200);
  const j2 = await ok2.json();
  assert.equal(j2.newly_minted, false);
  assert.equal(j2.seal.seat_number, 1);
  assert.equal(j2.seal.claim_code, j1.seal.claim_code);

  // Second outsider Mac joins -> mints Founding Circle #2!
  const nodeB = "b2c3d4e5f60718293a4b5c6d7e8f9011";
  const okB = await handlePulse(
    new Request("https://hive.sanctum.run/pulse", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        node_id: nodeB,
        event: "join",
        chip: "Apple M3 Ultra",
        memory_gb: 96,
        country: "DE",
        cli_version: "1.0.5",
      }),
    }),
    env,
    t0 + 7200_000
  );
  const jB = await okB.json();
  assert.equal(jB.seal.seat_number, 2);
  assert.equal(jB.seal.tier, "founding-circle");
  assert.match(jB.seal.claim_code, /^CIRCLE2-[A-F0-9]{4}-[A-F0-9]{4}$/);

  // Public seal verifier confirms Seed #1 with zero PII
  const vRes = await handleVerifySeal(
    new Request(`https://hive.sanctum.run/verify-seal?code=${j1.seal.claim_code}`),
    env
  );
  assert.equal(vRes.status, 200);
  const vData = await vRes.json();
  assert.equal(vData.valid, true);
  assert.equal(vData.seat_number, 1);
  assert.equal(vData.tier, "seed-1");
  assert.equal(vData.chip, "Apple M4 Max");
  assert.equal(vData.country, "FR");
  assert.equal(JSON.stringify(vData).includes(nodeA), false);

  // Bogus code returns 404 valid=false
  const badVerify = await handleVerifySeal(
    new Request("https://hive.sanctum.run/verify-seal?code=SEED1-0000-0000"),
    env
  );
  assert.equal(badVerify.status, 404);

  // Version check reports 1.0.7
  const latestRes = await handleLatestJson(
    new Request("https://hive.sanctum.run/latest.json?v=1.0.7&os=macos"),
    env,
    null,
    t0
  );
  assert.equal(latestRes.status, 200);
  const latestData = await latestRes.json();
  assert.equal(latestData.latest_version, "1.0.7");
  assert.equal(latestData.rust_tag, "rust-v1.0.3");

  // Analytics exposes milestones cleanly with zero PII & zero claim_code leak
  const aRes = await handleAnalytics(env, t0 + 7200_000);
  assert.equal(aRes.status, 200);
  const analytics = await aRes.json();
  assert.equal(analytics.total_nodes, 3);
  assert.equal(analytics.milestones.seed_zero.nodes, 1);
  assert.equal(analytics.milestones.seed_one.claimed, true);
  assert.equal(analytics.milestones.seed_one.chip, "Apple M4 Max");
  assert.equal(analytics.milestones.founding_circle.claimed, 1);
  assert.equal(analytics.milestones.founding_circle.total, 9);
  assert.equal(JSON.stringify(analytics).includes(j1.seal.claim_code), false);

  // DELETE /pulse/:node_id removes cleanly
  const delRes = await handleDeletePulse(nodeA, env);
  assert.equal(delRes.status, 200);
  assert.equal((await delRes.json()).removed, true);
  assert.equal(db._nodes.size, 2);
});

test("install-event records zero-PII aggregate funnel steps, rejects invalid input, and aggregates in /analytics", async () => {
  const db = createMockDb();
  const env = { DB: db };
  const t0 = Date.parse("2026-11-27T18:00:00Z");

  // Invalid step rejected with 400
  const badStep = await handleInstallEvent(
    new Request("https://hive.sanctum.run/install-event", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ step: "not_a_real_step" }),
    }),
    env,
    t0
  );
  assert.equal(badStep.status, 400);

  // Oversized payload rejected with 413
  const tooBig = await handleInstallEvent(
    new Request("https://hive.sanctum.run/install-event", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Content-Length": "4096" },
      body: JSON.stringify({ step: "bootstrap_started" }),
    }),
    env,
    t0
  );
  assert.equal(tooBig.status, 413);

  // Valid funnel progression (with CF-Connecting-IP header that MUST NEVER be stored)
  const steps = [
    { step: "bootstrap_started", cli_version: "unknown", os_major: "macOS 26", country: "FR" },
    { step: "clt_missing", cli_version: "unknown", os_major: "macOS 26", country: "FR" },
    { step: "cli_installed", cli_version: "v1.0.7", os_major: "macOS 26", country: "FR" },
    { step: "bootstrap_completed", cli_version: "1.0.7", os_major: "macOS 26", country: "FR" },
    { step: "bootstrap_started", cli_version: "unknown", os_major: "macOS 15", country: "US" },
    { step: "cli_installed", cli_version: "1.0.7", os_major: "macOS 15", country: "US" },
  ];

  for (const payload of steps) {
    const res = await handleInstallEvent(
      new Request("https://hive.sanctum.run/install-event", {
        method: "POST",
        headers: { "Content-Type": "application/json", "CF-Connecting-IP": "198.51.100.42" },
        body: JSON.stringify(payload),
      }),
      env,
      t0
    );
    assert.equal(res.status, 200);
    const body = await res.json();
    assert.equal(body.ok, true);
    assert.equal(body.zero_pii, true);
  }

  // Zero IP stored anywhere in mock D1
  const serialized = JSON.stringify([...db._installFunnel.entries()]);
  assert.equal(serialized.includes("198.51.100.42"), false);

  // Analytics exposes exact funnel aggregates
  const aRes = await handleAnalytics(env, t0 + 60_000);
  assert.equal(aRes.status, 200);
  const analytics = await aRes.json();
  assert.equal(analytics.install_funnel.totals.bootstrap_started, 2);
  assert.equal(analytics.install_funnel.totals.clt_missing, 1);
  assert.equal(analytics.install_funnel.totals.cli_installed, 2);
  assert.equal(analytics.install_funnel.totals.bootstrap_completed, 1);
  assert.equal(analytics.install_funnel.last_7d.cli_installed, 2);
  assert.equal(analytics.install_funnel.by_country.FR, 1);
  assert.equal(analytics.install_funnel.by_country.US, 1);
  assert.equal(analytics.install_funnel.by_os["macOS 26"], 1);
  assert.equal(analytics.install_funnel.by_os["macOS 15"], 1);
  assert.equal(analytics.install_funnel.by_version["1.0.7"], 2);
  assert.equal(analytics.install_funnel.daily.length, 1);
  assert.equal(analytics.install_funnel.daily[0].date, "2026-11-27");
  assert.equal(analytics.install_funnel.daily[0].cli_installed, 2);
});

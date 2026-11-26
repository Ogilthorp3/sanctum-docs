import test from "node:test";
import assert from "node:assert/strict";
import worker, {
  handleAnalytics,
  handleDeletePulse,
  handleLatestJson,
  handlePulse,
} from "../src/index.js";

/**
 * Minimal in-memory D1 mock supporting the exact SQL statements in src/index.js.
 */
function createMockDb() {
  const nodes = new Map();
  const versionChecks = new Map(); // key: `${date}|${cli_version}|${os_family}` -> count

  return {
    _nodes: nodes,
    _versionChecks: versionChecks,
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
          throw new Error(`Unhandled run SQL: ${sql}`);
        },
        async first() {
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
          throw new Error(`Unhandled all SQL: ${sql}`);
        },
      };
      return stmt;
    },
  };
}

test("health endpoint reports zero_pii", async () => {
  const res = await worker.fetch(new Request("https://hive.sanctum.run/health"), { DB: createMockDb() });
  assert.equal(res.status, 200);
  const data = await res.json();
  assert.equal(data.ok, true);
  assert.equal(data.zero_pii, true);
});

test("pulse rejects invalid node_id and accepts valid onboard + heartbeat", async () => {
  const db = createMockDb();
  const env = { DB: db };
  const t0 = Date.parse("2026-11-26T15:00:00Z");

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

  // Valid onboard pulse (explicitly includes a spoofed IP header which MUST be ignored)
  const nodeA = "a1b2c3d4e5f60718293a4b5c6d7e8f90";
  const ok1 = await handlePulse(
    new Request("https://hive.sanctum.run/pulse", {
      method: "POST",
      headers: { "Content-Type": "application/json", "CF-Connecting-IP": "1.2.3.4" },
      body: JSON.stringify({
        node_id: nodeA,
        event: "onboard",
        chip: "Apple M4 Pro",
        memory_gb: 64,
        os_version: "macOS 26.1",
        country: "ca",
        cli_version: "v1.0.1",
        modules: ["backup", "link", "INVALID!"],
      }),
    }),
    env,
    t0
  );
  assert.equal(ok1.status, 200);
  const j1 = await ok1.json();
  assert.equal(j1.hive_nodes, 1);
  assert.equal(j1.active_7d, 1);

  // Verify zero IP stored anywhere
  const stored = db._nodes.get(nodeA);
  assert.equal(stored.country, "CA");
  assert.equal(stored.cli_version, "1.0.1");
  assert.equal(stored.onboard_completed, 1);
  assert.equal(stored.modules_json, '["backup","link"]');
  assert.equal(JSON.stringify(stored).includes("1.2.3.4"), false);

  // Second heartbeat does not overwrite onboard_completed or double count node
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
  assert.equal(db._nodes.size, 1);
  assert.equal(db._nodes.get(nodeA).onboard_completed, 1);
  assert.equal(db._nodes.get(nodeA).pulse_count, 2);

  // Version check increments zero-ID counter
  const latestRes = await handleLatestJson(
    new Request("https://hive.sanctum.run/latest.json?v=1.0.1&os=macos"),
    env,
    null,
    t0
  );
  assert.equal(latestRes.status, 200);
  const latestData = await latestRes.json();
  assert.equal(latestData.latest_version, "1.0.1");

  // Analytics returns aggregate summary + daily buckets
  const aRes = await handleAnalytics(env, t0 + 3600_000);
  assert.equal(aRes.status, 200);
  const analytics = await aRes.json();
  assert.equal(analytics.total_nodes, 1);
  assert.equal(analytics.seed_zero_online, true);
  assert.equal(analytics.seed_zero_since, "2026-11-26");
  assert.equal(analytics.onboard_completed, 1);
  assert.equal(analytics.total_ram_gb, 64);
  assert.deepEqual(analytics.by_chip, { "Apple M4 Pro": 1 });
  assert.deepEqual(analytics.by_country, { CA: 1 });
  assert.deepEqual(analytics.by_module, { backup: 1, link: 1 });
  assert.equal(analytics.version_checks_24h, 1);
  assert.equal(analytics.daily_installs.length, 1);

  // DELETE /pulse/:node_id removes the node cleanly (`sanctum hive leave`)
  const delRes = await handleDeletePulse(nodeA, env);
  assert.equal(delRes.status, 200);
  const delData = await delRes.json();
  assert.equal(delData.removed, true);
  assert.equal(db._nodes.size, 0);
});

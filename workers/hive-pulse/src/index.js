/**
 * Sovereign Sanctum Hive Pulse — Cloudflare Worker (hive.sanctum.run)
 *
 * Privacy-first, zero-PII aggregate counter & Sovereign Seal minter for the Sanctum Hive.
 * - NEVER reads, logs, hashes, or stores CF-Connecting-IP, X-Forwarded-For,
 *   User-Agent, hostnames, usernames, file paths, or prompts.
 * - Opt-in nodes identify only via a locally generated anonymous hex ID
 *   (Ed25519 pubkey hash or random token) and can erase themselves anytime via
 *   DELETE /pulse/:node_id (`sanctum hive leave`).
 * - First sovereign node beyond Seed #0 (Founder's Fleet) automatically mints
 *   `Seed #1 — First Beyond the Walls`, and seats #2–#10 mint `Founding Circle`,
 *   complete with an HMAC-SHA256 verifiable, zero-PII Sovereign Seal.
 * - Public aggregate stats are open at GET /analytics for both operators and
 *   the public sanctum.run Hive counter.
 */

const LATEST_VERSION = "1.0.6";
const MIN_SUPPORTED_VERSION = "1.0.0";
const RELEASE_URL = "https://github.com/Ogilthorp3/sanctum-cli/releases/latest";
const SOURCE_URL = "https://github.com/Ogilthorp3/sanctum-docs/tree/main/workers/hive-pulse";
const RUST_TAG = "rust-v1.0.3";
const RUST_URL = "https://github.com/Ogilthorp3/homebrew-sanctum/releases/download/rust-v1.0.3/sanctum-rust-suite-arm64.tar.gz";
const RUST_SHA256 = "8c1bd11514762f401444d78d9c4723023607ca7f7ac1f132eb0b0c258bc2639e";
const DRAGON_TAG = "dragon-2";
const DRAGON_ADAPTER = "qwen-haus-dragon-193d2d7407ec";
const DRAGON_URL = "https://github.com/Ogilthorp3/homebrew-sanctum/releases/download/dragon-2/sanctum-dragon-guest.zip";
const DRAGON_SHA256 = "1defbb9c13269bc6bfa40e83cae38e92716dc915a46ac385a1e2c3a61f52bf61";
const MLX_LM_VERSION = "0.32.2";
const OPENCLAW_VERSION = "2026.11.10";
const SIGNAL_CLI_VERSION = "0.14.10";

const NODE_ID_RE = /^[a-f0-9]{16,64}$/i;
const CLAIM_CODE_RE = /^[A-Z0-9-]{8,32}$/;
const COUNTRY_RE = /^[A-Z]{2}$/;
const VERSION_RE = /^[0-9A-Za-z._+-]{1,24}$/;
const MODULE_RE = /^[a-z0-9_-]{1,32}$/;
const VALID_EVENTS = new Set(["onboard", "heartbeat", "backup", "status", "join"]);

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type",
};

function jsonResponse(body, status = 200, extraHeaders = {}) {
  return new Response(JSON.stringify(body, null, 2) + "\n", {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      ...CORS_HEADERS,
      ...extraHeaders,
    },
  });
}

function cleanStr(val, fallback, maxLen = 64) {
  if (typeof val !== "string") return fallback;
  const trimmed = val.replace(/[\r\n\t\x00-\x1f\x7f]/g, " ").trim();
  if (!trimmed) return fallback;
  return trimmed.slice(0, maxLen);
}

function cleanCountry(val) {
  if (typeof val !== "string") return "ZZ";
  const upper = val.trim().toUpperCase().slice(0, 2);
  return COUNTRY_RE.test(upper) ? upper : "ZZ";
}

function cleanVersion(val) {
  if (typeof val !== "string") return "unknown";
  const v = val.trim().replace(/^v/i, "").slice(0, 24);
  return VERSION_RE.test(v) ? v : "unknown";
}

function cleanMemoryGb(val) {
  const n = Number(val);
  if (!Number.isFinite(n) || n < 0) return 0;
  return Math.min(2048, Math.round(n));
}

function cleanModules(val) {
  if (!Array.isArray(val)) return [];
  const out = [];
  const seen = new Set();
  for (const item of val) {
    if (typeof item !== "string") continue;
    const slug = item.trim().toLowerCase();
    if (MODULE_RE.test(slug) && !seen.has(slug)) {
      seen.add(slug);
      out.push(slug);
      if (out.length >= 20) break;
    }
  }
  return out.sort();
}

function isoDateDaysAgo(nowMs, days) {
  return new Date(nowMs - days * 86_400_000).toISOString().slice(0, 10);
}

function isoTimestampHoursAgo(nowMs, hours) {
  return new Date(nowMs - hours * 3_600_000).toISOString();
}

function bytesToHex(buf) {
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function sha256Hex(text) {
  const data = new TextEncoder().encode(text);
  const digest = await crypto.subtle.digest("SHA-256", data);
  return bytesToHex(digest);
}

async function hmacSha256Hex(secret, message) {
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(message));
  return bytesToHex(sig);
}

export function describeSeat(seatNumber) {
  const seat = Number(seatNumber ?? 0);
  if (seat <= 0) {
    return {
      seat_number: 0,
      tier: "seed-0",
      title: "Seed #0 — Founder's Fleet",
      short_badge: "SEED #0",
      motto: "Where the Sanctum wall was raised.",
    };
  }
  if (seat === 1) {
    return {
      seat_number: 1,
      tier: "seed-1",
      title: "Seed #1 — First Beyond the Walls",
      short_badge: "SEED #1",
      motto: "First sovereign Mac to answer from beyond the Founder's Fleet.",
    };
  }
  if (seat <= 10) {
    return {
      seat_number: seat,
      tier: "founding-circle",
      title: `Founding Circle #${seat}`,
      short_badge: `FOUNDING #${seat}`,
      motto: "Among the first ten sovereign nodes of the Sanctum Hive.",
    };
  }
  if (seat <= 100) {
    return {
      seat_number: seat,
      tier: "vanguard",
      title: `Beta Vanguard #${seat}`,
      short_badge: `VANGUARD #${seat}`,
      motto: "Early sovereign pioneer of the Sanctum public beta.",
    };
  }
  return {
    seat_number: seat,
    tier: "sovereign",
    title: `Sovereign Node #${seat}`,
    short_badge: `NODE #${seat}`,
    motto: "Local silicon, zero cloud leash.",
  };
}

function formatClaimCode(seatNumber, sigHex) {
  const s = sigHex.slice(0, 8).toUpperCase();
  const partA = s.slice(0, 4);
  const partB = s.slice(4, 8);
  if (seatNumber <= 0) return `SEED0-${partA}-${partB}`;
  if (seatNumber === 1) return `SEED1-${partA}-${partB}`;
  if (seatNumber <= 10) return `CIRCLE${seatNumber}-${partA}-${partB}`;
  if (seatNumber <= 100) return `VANGUARD${seatNumber}-${partA}`;
  return `HIVE${seatNumber}-${partA}`;
}

async function mintSealObject({ env, nodeId, seatNumber, firstSeenAt, chip, memoryGb, country, existingCode }) {
  const meta = describeSeat(seatNumber);
  const secret = env.SEAL_SECRET || "sanctum-hive-public-commitment-v1";
  const payloadStr = `sanctum-seal-v1:${nodeId}:${meta.seat_number}:${firstSeenAt}`;
  const signature = await hmacSha256Hex(secret, payloadStr);
  const claimCode = existingCode || formatClaimCode(meta.seat_number, signature);
  const publicHash = (
    await sha256Hex(`sanctum-public-v1:${meta.seat_number}:${firstSeenAt}:${chip}:${memoryGb}:${country}`)
  ).slice(0, 16);

  return {
    ...meta,
    minted_at: firstSeenAt,
    claim_code: claimCode,
    signature,
    public_hash: publicHash,
    verify_url: `https://hive.sanctum.run/verify-seal?code=${encodeURIComponent(claimCode)}`,
  };
}

export async function handlePulse(request, env, nowMs = Date.now()) {
  const len = Number(request.headers.get("content-length") || "0");
  if (len > 8192) {
    return jsonResponse({ ok: false, error: "payload_too_large" }, 413);
  }

  let body;
  try {
    body = await request.json();
  } catch {
    return jsonResponse({ ok: false, error: "invalid_json" }, 400);
  }

  if (!body || typeof body !== "object" || Array.isArray(body)) {
    return jsonResponse({ ok: false, error: "expected_object" }, 400);
  }

  const rawId = typeof body.node_id === "string" ? body.node_id.trim().toLowerCase() : "";
  if (!NODE_ID_RE.test(rawId)) {
    return jsonResponse(
      { ok: false, error: "invalid_node_id", hint: "expected 16-64 hex characters" },
      400
    );
  }

  const event = typeof body.event === "string" && VALID_EVENTS.has(body.event.trim().toLowerCase())
    ? body.event.trim().toLowerCase()
    : "heartbeat";
  const onboardCompleted = event === "onboard" || body.onboard_completed === true ? 1 : 0;
  const chip = cleanStr(body.chip, "Unknown", 64);
  const memoryGb = cleanMemoryGb(body.memory_gb);
  const osVersion = cleanStr(body.os_version, "Unknown", 32);
  const country = cleanCountry(body.country);
  const cliVersion = cleanVersion(body.cli_version);
  const modulesJson = JSON.stringify(cleanModules(body.modules));

  const nowIso = new Date(nowMs).toISOString();
  const today = nowIso.slice(0, 10);

  const existing = await env.DB.prepare(
    "SELECT seat_number, claim_code, first_seen_at, chip, memory_gb, country FROM nodes WHERE node_id = ?"
  )
    .bind(rawId)
    .first();

  let assignedSeat;
  let mintedAt;
  let existingCode = null;
  let isNewlyMinted = false;

  if (existing) {
    assignedSeat = Number(existing.seat_number ?? 0);
    mintedAt = existing.first_seen_at || nowIso;
    existingCode = existing.claim_code || null;
  } else {
    isNewlyMinted = true;
    mintedAt = nowIso;
  }

  let seal = null;
  for (let attempt = 0; attempt < 3; attempt += 1) {
    if (!existing) {
      const maxRow = await env.DB.prepare("SELECT COALESCE(MAX(seat_number), 0) AS max_seat FROM nodes").first();
      assignedSeat = Number(maxRow?.max_seat ?? 0) + 1;
    }

    const effectiveChip = chip !== "Unknown" ? chip : (existing?.chip || "Unknown");
    const effectiveRam = memoryGb > 0 ? memoryGb : Number(existing?.memory_gb || 0);
    const effectiveCountry = country !== "ZZ" ? country : (existing?.country || "ZZ");

    seal = await mintSealObject({
      env,
      nodeId: rawId,
      seatNumber: assignedSeat,
      firstSeenAt: mintedAt,
      chip: effectiveChip,
      memoryGb: effectiveRam,
      country: effectiveCountry,
      existingCode,
    });

    try {
      await env.DB.prepare(
        `INSERT INTO nodes (
           node_id, seat_number, claim_code, first_seen_date, first_seen_at, last_seen_at,
           onboard_completed, chip, memory_gb, os_version, country,
           cli_version, modules_json, pulse_count
         ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
         ON CONFLICT(node_id) DO UPDATE SET
           claim_code = COALESCE(nodes.claim_code, excluded.claim_code),
           last_seen_at = excluded.last_seen_at,
           onboard_completed = MAX(nodes.onboard_completed, excluded.onboard_completed),
           chip = CASE WHEN excluded.chip != 'Unknown' THEN excluded.chip ELSE nodes.chip END,
           memory_gb = CASE WHEN excluded.memory_gb > 0 THEN excluded.memory_gb ELSE nodes.memory_gb END,
           os_version = CASE WHEN excluded.os_version != 'Unknown' THEN excluded.os_version ELSE nodes.os_version END,
           country = CASE WHEN excluded.country != 'ZZ' THEN excluded.country ELSE nodes.country END,
           cli_version = CASE WHEN excluded.cli_version != 'unknown' THEN excluded.cli_version ELSE nodes.cli_version END,
           modules_json = CASE WHEN excluded.modules_json != '[]' THEN excluded.modules_json ELSE nodes.modules_json END,
           pulse_count = nodes.pulse_count + 1`
      )
        .bind(
          rawId,
          assignedSeat,
          seal.claim_code,
          today,
          mintedAt,
          nowIso,
          onboardCompleted,
          chip,
          memoryGb,
          osVersion,
          country,
          cliVersion,
          modulesJson
        )
        .run();
      break;
    } catch (err) {
      if (attempt === 2 || !String(err).includes("UNIQUE")) {
        throw err;
      }
    }
  }

  const cutoff7d = isoTimestampHoursAgo(nowMs, 24 * 7);
  const counts = await env.DB.prepare(
    `SELECT
       COUNT(*) AS total_nodes,
       SUM(CASE WHEN last_seen_at >= ? THEN 1 ELSE 0 END) AS active_7d
     FROM nodes`
  )
    .bind(cutoff7d)
    .first();

  return jsonResponse({
    ok: true,
    event,
    hive_nodes: Number(counts?.total_nodes || 0),
    active_7d: Number(counts?.active_7d || 0),
    newly_minted: isNewlyMinted,
    seal,
    zero_pii: true,
  });
}

export async function handleVerifySeal(request, env) {
  const url = new URL(request.url);
  const rawCode = (url.searchParams.get("code") || "").trim().toUpperCase();
  if (!CLAIM_CODE_RE.test(rawCode)) {
    return jsonResponse({ ok: false, valid: false, error: "invalid_claim_code" }, 400);
  }

  const row = await env.DB.prepare(
    `SELECT seat_number, first_seen_date, first_seen_at, chip, memory_gb, country
     FROM nodes
     WHERE claim_code = ?
     LIMIT 1`
  )
    .bind(rawCode)
    .first();

  if (!row) {
    return jsonResponse({ ok: true, valid: false, zero_pii: true }, 404);
  }

  const meta = describeSeat(row.seat_number);
  const publicHash = (
    await sha256Hex(
      `sanctum-public-v1:${meta.seat_number}:${row.first_seen_at}:${row.chip}:${row.memory_gb}:${row.country}`
    )
  ).slice(0, 16);

  return jsonResponse(
    {
      ok: true,
      valid: true,
      zero_pii: true,
      ...meta,
      minted_date: row.first_seen_date,
      minted_at: row.first_seen_at,
      chip: row.chip,
      memory_gb: Number(row.memory_gb || 0),
      country: row.country,
      public_hash: publicHash,
    },
    200,
    { "Cache-Control": "public, max-age=60, s-maxage=60" }
  );
}

export async function handleDeletePulse(nodeId, env) {
  const cleanId = String(nodeId || "").trim().toLowerCase();
  if (!NODE_ID_RE.test(cleanId)) {
    return jsonResponse({ ok: false, error: "invalid_node_id" }, 400);
  }
  const res = await env.DB.prepare("DELETE FROM nodes WHERE node_id = ?").bind(cleanId).run();
  const changes = Number(res?.meta?.changes ?? 0);
  return jsonResponse({ ok: true, removed: changes > 0 });
}

export async function handleLatestJson(request, env, ctx, nowMs = Date.now()) {
  const url = new URL(request.url);
  const cliVersion = cleanVersion(url.searchParams.get("v") || "unknown");
  const osFamily = cleanStr(url.searchParams.get("os") || "unknown", "unknown", 24).toLowerCase();
  const today = new Date(nowMs).toISOString().slice(0, 10);

  // Increment zero-ID daily aggregate counter asynchronously (never blocks response)
  const writePromise = env.DB.prepare(
    `INSERT INTO daily_version_checks (date, cli_version, os_family, checks)
     VALUES (?, ?, ?, 1)
     ON CONFLICT(date, cli_version, os_family) DO UPDATE SET
       checks = daily_version_checks.checks + 1`
  )
    .bind(today, cliVersion, osFamily)
    .run()
    .catch(() => {});

  if (ctx && typeof ctx.waitUntil === "function") {
    ctx.waitUntil(writePromise);
  } else {
    await writePromise;
  }

  return jsonResponse(
    {
      latest_version: env.LATEST_VERSION || LATEST_VERSION,
      min_supported: env.MIN_SUPPORTED_VERSION || MIN_SUPPORTED_VERSION,
      release_url: RELEASE_URL,
      upgrade_cmd: "sanctum update",
      rust_tag: env.RUST_TAG || RUST_TAG,
      rust_url: env.RUST_URL || RUST_URL,
      rust_sha256: env.RUST_SHA256 || RUST_SHA256,
      dragon_tag: env.DRAGON_TAG || DRAGON_TAG,
      dragon_adapter: env.DRAGON_ADAPTER || DRAGON_ADAPTER,
      dragon_url: env.DRAGON_URL || DRAGON_URL,
      dragon_sha256: env.DRAGON_SHA256 || DRAGON_SHA256,
      mlx_lm_version: env.MLX_LM_VERSION || MLX_LM_VERSION,
      openclaw_version: env.OPENCLAW_VERSION || OPENCLAW_VERSION,
      signal_cli_version: env.SIGNAL_CLI_VERSION || SIGNAL_CLI_VERSION,
    },
    200,
    { "Cache-Control": "public, max-age=300, s-maxage=300" }
  );
}

export async function handleAnalytics(env, nowMs = Date.now()) {
  const cutoff24h = isoTimestampHoursAgo(nowMs, 24);
  const cutoff7d = isoTimestampHoursAgo(nowMs, 24 * 7);
  const cutoff30d = isoTimestampHoursAgo(nowMs, 24 * 30);
  const sinceDate = isoDateDaysAgo(nowMs, 305);
  const todayDate = new Date(nowMs).toISOString().slice(0, 10);
  const date7d = isoDateDaysAgo(nowMs, 7);

  const summary = await env.DB.prepare(
    `SELECT
       COUNT(*) AS total_nodes,
       SUM(CASE WHEN onboard_completed = 1 THEN 1 ELSE 0 END) AS onboard_completed,
       SUM(CASE WHEN last_seen_at >= ? THEN 1 ELSE 0 END) AS active_24h,
       SUM(CASE WHEN last_seen_at >= ? THEN 1 ELSE 0 END) AS active_7d,
       SUM(CASE WHEN last_seen_at >= ? THEN 1 ELSE 0 END) AS active_30d,
       COALESCE(SUM(memory_gb), 0) AS total_ram_gb,
       MIN(first_seen_date) AS seed_zero_since
     FROM nodes`
  )
    .bind(cutoff24h, cutoff7d, cutoff30d)
    .first();

  const chipRows = (
    await env.DB.prepare(
      "SELECT chip, COUNT(*) AS cnt FROM nodes GROUP BY chip ORDER BY cnt DESC LIMIT 20"
    ).all()
  ).results || [];

  const countryRows = (
    await env.DB.prepare(
      "SELECT country, COUNT(*) AS cnt FROM nodes GROUP BY country ORDER BY cnt DESC LIMIT 30"
    ).all()
  ).results || [];

  const versionRows = (
    await env.DB.prepare(
      "SELECT cli_version, COUNT(*) AS cnt FROM nodes GROUP BY cli_version ORDER BY cnt DESC LIMIT 20"
    ).all()
  ).results || [];

  const moduleRows = (
    await env.DB.prepare("SELECT modules_json FROM nodes").all()
  ).results || [];

  const milestoneRows = (
    await env.DB.prepare(
      `SELECT seat_number, first_seen_date, first_seen_at, chip, memory_gb, country
       FROM nodes
       WHERE seat_number IS NOT NULL AND seat_number <= 10
       ORDER BY seat_number ASC`
    ).all()
  ).results || [];

  const byModule = {};
  for (const row of moduleRows) {
    try {
      const mods = JSON.parse(row.modules_json || "[]");
      if (Array.isArray(mods)) {
        for (const m of mods) {
          byModule[m] = (byModule[m] || 0) + 1;
        }
      }
    } catch {
      /* ignore */
    }
  }

  let seedZeroNodes = 0;
  let seedZeroRam = 0;
  let seedOne = null;
  const foundingSeats = [];

  for (const row of milestoneRows) {
    const seat = Number(row.seat_number ?? 0);
    if (seat <= 0) {
      seedZeroNodes += 1;
      seedZeroRam += Number(row.memory_gb || 0);
    } else if (seat === 1) {
      const publicHash = (
        await sha256Hex(
          `sanctum-public-v1:1:${row.first_seen_at}:${row.chip}:${row.memory_gb}:${row.country}`
        )
      ).slice(0, 12);
      seedOne = {
        claimed: true,
        seat_number: 1,
        chip: row.chip,
        ram_gb: Number(row.memory_gb || 0),
        country: row.country,
        since: row.first_seen_date,
        public_hash: publicHash,
      };
    } else if (seat <= 10) {
      foundingSeats.push({
        seat_number: seat,
        chip: row.chip,
        ram_gb: Number(row.memory_gb || 0),
        country: row.country,
        since: row.first_seen_date,
      });
    }
  }

  const dailyInstallsRows = (
    await env.DB.prepare(
      `SELECT
         first_seen_date AS date,
         COUNT(*) AS new_nodes,
         SUM(CASE WHEN onboard_completed = 1 THEN 1 ELSE 0 END) AS onboarded
       FROM nodes
       WHERE first_seen_date >= ?
       GROUP BY first_seen_date
       ORDER BY first_seen_date ASC`
    )
      .bind(sinceDate)
      .all()
  ).results || [];

  const dailyVersionChecksRows = (
    await env.DB.prepare(
      `SELECT date, SUM(checks) AS checks
       FROM daily_version_checks
       WHERE date >= ?
       GROUP BY date
       ORDER BY date ASC`
    )
      .bind(sinceDate)
      .all()
  ).results || [];

  const totalNodes = Number(summary?.total_nodes || 0);
  const totalRamGb = Number(summary?.total_ram_gb || 0);

  const byChip = {};
  for (const r of chipRows) byChip[r.chip] = Number(r.cnt || 0);

  const byCountry = {};
  for (const r of countryRows) byCountry[r.country] = Number(r.cnt || 0);

  const byVersion = {};
  for (const r of versionRows) byVersion[r.cli_version] = Number(r.cnt || 0);

  const dailyInstalls = dailyInstallsRows.map((r) => ({
    date: r.date,
    new_nodes: Number(r.new_nodes || 0),
    onboarded: Number(r.onboarded || 0),
  }));

  const dailyVersionChecks = dailyVersionChecksRows.map((r) => ({
    date: r.date,
    checks: Number(r.checks || 0),
  }));

  const versionChecks24h = dailyVersionChecks
    .filter((r) => r.date >= isoDateDaysAgo(nowMs, 1) && r.date <= todayDate)
    .reduce((acc, r) => acc + r.checks, 0);

  const versionChecks7d = dailyVersionChecks
    .filter((r) => r.date >= date7d)
    .reduce((acc, r) => acc + r.checks, 0);

  return jsonResponse(
    {
      ok: true,
      generated_at: new Date(nowMs).toISOString(),
      zero_pii: true,
      source_url: SOURCE_URL,
      total_nodes: totalNodes,
      seed_zero_online: totalNodes > 0,
      seed_zero_since: summary?.seed_zero_since || null,
      milestones: {
        seed_zero: {
          nodes: seedZeroNodes,
          ram_gb: seedZeroRam,
          since: summary?.seed_zero_since || null,
        },
        seed_one: seedOne || { claimed: false, seat_number: 1 },
        founding_circle: {
          claimed: foundingSeats.length,
          total: 9,
          seats: foundingSeats,
        },
      },
      onboard_completed: Number(summary?.onboard_completed || 0),
      active_24h: Number(summary?.active_24h || 0),
      active_7d: Number(summary?.active_7d || 0),
      active_30d: Number(summary?.active_30d || 0),
      total_ram_gb: totalRamGb,
      avg_ram_gb: totalNodes > 0 ? Math.round((totalRamGb / totalNodes) * 10) / 10 : 0,
      version_checks_24h: versionChecks24h,
      version_checks_7d: versionChecks7d,
      by_chip: byChip,
      by_country: byCountry,
      by_version: byVersion,
      by_module: byModule,
      daily_installs: dailyInstalls,
      daily_version_checks: dailyVersionChecks,
    },
    200,
    { "Cache-Control": "public, max-age=120, s-maxage=120" }
  );
}

async function handleAnalyticsCached(request, env, ctx) {
  const cache = typeof caches !== "undefined" ? caches.default : null;
  const cacheKey = cache ? new Request("https://hive.sanctum.run/analytics", { method: "GET" }) : null;
  if (cache && cacheKey) {
    const hit = await cache.match(cacheKey);
    if (hit) return hit;
  }
  const resp = await handleAnalytics(env);
  if (cache && cacheKey && resp.status === 200) {
    const putPromise = cache.put(cacheKey, resp.clone()).catch(() => {});
    if (ctx && typeof ctx.waitUntil === "function") {
      ctx.waitUntil(putPromise);
    } else {
      await putPromise;
    }
  }
  return resp;
}

export default {
  async fetch(request, env, ctx) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";

    if (request.method === "GET" && (path === "/" || path === "/health")) {
      return jsonResponse({
        ok: true,
        service: "sanctum-hive-pulse",
        zero_pii: true,
        endpoints: [
          "/health",
          "/analytics",
          "/latest.json",
          "/verify-seal?code=...",
          "POST /pulse",
          "DELETE /pulse/:node_id",
        ],
        source_url: SOURCE_URL,
      });
    }

    if (request.method === "POST" && path === "/pulse") {
      return handlePulse(request, env);
    }

    if (request.method === "DELETE" && path.startsWith("/pulse/")) {
      const nodeId = path.slice("/pulse/".length);
      return handleDeletePulse(nodeId, env);
    }

    if (request.method === "GET" && path === "/latest.json") {
      return handleLatestJson(request, env, ctx);
    }

    if (request.method === "GET" && path === "/verify-seal") {
      return handleVerifySeal(request, env);
    }

    if (request.method === "GET" && path === "/analytics") {
      return handleAnalyticsCached(request, env, ctx);
    }

    return jsonResponse({ ok: false, error: "not_found" }, 404);
  },
};

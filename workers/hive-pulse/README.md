# Sovereign Sanctum Hive Pulse (`https://hive.sanctum.run`)

Publicly auditable, zero-PII Cloudflare Worker + D1 aggregate counter for the Sanctum Hive.

## Privacy contract (verifiable in `src/index.js`)

- **Opt-in only** for node heartbeats (`sanctum onboard` asks explicitly, or `sanctum hive join`).
- **Zero PII**: never reads, logs, hashes, or stores IP addresses, hostnames, usernames, file paths, or prompts.
- **Anonymous ID**: nodes generate a random/Ed25519 hex ID locally; `sanctum hive leave` (`DELETE /pulse/:node_id`) erases the row immediately.
- **Zero-ID version check**: `GET /latest.json?v=<version>&os=macos` increments only a daily aggregate count per CLI version/OS (opt-out via `SANCTUM_NO_UPDATE_CHECK=1`).
- **Zero-ID install funnel**: `POST /install-event` records only a daily aggregate count per `(step, cli_version, os_major, country)` during `install.sh` bootstrap — zero IP, zero machine ID, auto-skipped in CI, and opt-out via `SANCTUM_NO_TELEMETRY=1` or `DO_NOT_TRACK=1`.
- **Open aggregate stats**: `GET /analytics` returns the exact totals visible to everyone.

## Test & Deploy

```bash
node --test test/worker.test.mjs
npx wrangler d1 execute sanctum-hive-pulse --remote --file=schema.sql
npx wrangler deploy
```

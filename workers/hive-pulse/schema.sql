-- Sovereign Sanctum Hive Pulse — Zero-PII D1 Schema
-- Publicly auditable at https://github.com/Ogilthorp3/sanctum-docs/tree/main/workers/hive-pulse
-- Explicitly stores ZERO IP addresses, ZERO hostnames, ZERO usernames, ZERO prompts.

CREATE TABLE IF NOT EXISTS nodes (
  node_id TEXT PRIMARY KEY,
  first_seen_date TEXT NOT NULL,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  onboard_completed INTEGER NOT NULL DEFAULT 0,
  chip TEXT NOT NULL DEFAULT 'Unknown',
  memory_gb INTEGER NOT NULL DEFAULT 0,
  os_version TEXT NOT NULL DEFAULT 'Unknown',
  country TEXT NOT NULL DEFAULT 'ZZ',
  cli_version TEXT NOT NULL DEFAULT 'unknown',
  modules_json TEXT NOT NULL DEFAULT '[]',
  pulse_count INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_nodes_last_seen ON nodes(last_seen_at);
CREATE INDEX IF NOT EXISTS idx_nodes_first_date ON nodes(first_seen_date);

CREATE TABLE IF NOT EXISTS daily_version_checks (
  date TEXT NOT NULL,
  cli_version TEXT NOT NULL,
  os_family TEXT NOT NULL,
  checks INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (date, cli_version, os_family)
);

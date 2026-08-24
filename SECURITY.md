# Security Policy

This repository is the Sanctum documentation site (<https://sanctum.run>). It
ships no runtime code, so the security surface is different from a daemon's —
and in one respect sharper: **a docs leak is a security incident.** Pages here
describe a live home network, and the No-Leak Rule in
[CONTRIBUTING.md](./CONTRIBUTING.md) exists because a real IP, MAC, hostname,
GUID, or work-lane identifier in a public page is an exposure that no patch can
recall once it is indexed.

## Reporting

**Do not open a public GitHub issue.** Use either:

- **GitHub Security Advisories** — preferred. Draft one at
  <https://github.com/ogilthorp3/sanctum-docs/security/advisories/new>.
- **Email** — `security@sanctum.run`.

## Especially welcome

If you find any of the following on the published site, please tell us — these
are treated as incidents, not style nits:

- A real IP outside the documentation ranges, a real MAC, a resolvable
  hostname, or a real tailnet MagicDNS name.
- A credential value of any kind, even a revoked one.
- A GUID or UUID tied to a real account or tenant.
- An identifier that maps a private third party's internal systems — where
  their secrets live, what they are called, or verbatim paths into their
  documents.
- A real person's name, phone number, or address.

`scripts/contrib-check.py` enforces these patterns in CI over the full corpus on
every deploy. If you found something it missed, that is a checker bug as well as
a leak, and we want both halves of the report.

## What to Expect

- **Acknowledgement** within 3 business days.
- For a live exposure, we remove the content first and discuss second.
- Note that removal from the repo does not undo publication. We will say so
  plainly rather than imply a leak was contained when it was not.

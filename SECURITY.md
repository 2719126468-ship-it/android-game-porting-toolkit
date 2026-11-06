# Security Policy

## Supported use

Use AGPT only with software and assets you are authorized to inspect, modify, and port. AGPT is a development aid, not legal advice.

## Safe defaults

- The scanner does not execute inspected files.
- Symlinks are skipped; traversal does not follow them.
- The scanner reads a bounded prefix for signature hints and does not unpack archives in v0.1.0.
- Generated reports may contain local paths. Review them before sharing.
- Do not commit proprietary binaries, assets, save files, credentials, license tokens, or private keys.
- Build workers should run with least privilege and without access to unrelated personal files.

## Out of scope

Bypassing DRM, license checks, anti-cheat, online authentication, payment systems, or technical access controls; extracting or redistributing unauthorized game data; and deploying malware or cheats are not project goals.

## Reporting vulnerabilities

Please do not publish exploitable vulnerabilities involving user game files or build workers in a public issue. Contact the repository maintainers privately using the security contact configured on the Git hosting platform. Include reproduction steps, impact, and affected version. Do not include proprietary game files unless you have permission to share them.

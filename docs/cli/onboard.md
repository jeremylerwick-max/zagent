---
summary: "CLI reference for `zagent onboard` (interactive onboarding wizard)"
read_when:
  - You want guided setup for gateway, workspace, auth, channels, and skills
---

# `zagent onboard`

Interactive onboarding wizard (local or remote Gateway setup).

Related:
- Wizard guide: [Onboarding](/start/onboarding)

## Examples

```bash
zagent onboard
zagent onboard --flow quickstart
zagent onboard --flow manual
zagent onboard --mode remote --remote-url ws://gateway-host:18789
```

Flow notes:
- `quickstart`: minimal prompts, auto-generates a gateway token.
- `manual`: full prompts for port/bind/auth (alias of `advanced`).
- Fastest first chat: `zagent dashboard` (Control UI, no channel setup).

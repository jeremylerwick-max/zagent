---
summary: "CLI reference for `zagent voicecall` (voice-call plugin command surface)"
read_when:
  - You use the voice-call plugin and want the CLI entry points
  - You want quick examples for `voicecall call|continue|status|tail|expose`
---

# `zagent voicecall`

`voicecall` is a plugin-provided command. It only appears if the voice-call plugin is installed and enabled.

Primary doc:
- Voice-call plugin: [Voice Call](/plugins/voice-call)

## Common commands

```bash
zagent voicecall status --call-id <id>
zagent voicecall call --to "+15555550123" --message "Hello" --mode notify
zagent voicecall continue --call-id <id> --message "Any questions?"
zagent voicecall end --call-id <id>
```

## Exposing webhooks (Tailscale)

```bash
zagent voicecall expose --mode serve
zagent voicecall expose --mode funnel
zagent voicecall unexpose
```

Security note: only expose the webhook endpoint to networks you trust. Prefer Tailscale Serve over Funnel when possible.


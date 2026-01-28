---
summary: "CLI reference for `zagent tui` (terminal UI connected to the Gateway)"
read_when:
  - You want a terminal UI for the Gateway (remote-friendly)
  - You want to pass url/token/session from scripts
---

# `zagent tui`

Open the terminal UI connected to the Gateway.

Related:
- TUI guide: [TUI](/tui)

## Examples

```bash
zagent tui
zagent tui --url ws://127.0.0.1:18789 --token <token>
zagent tui --session main --deliver
```


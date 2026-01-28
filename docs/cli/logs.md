---
summary: "CLI reference for `zagent logs` (tail gateway logs via RPC)"
read_when:
  - You need to tail Gateway logs remotely (without SSH)
  - You want JSON log lines for tooling
---

# `zagent logs`

Tail Gateway file logs over RPC (works in remote mode).

Related:
- Logging overview: [Logging](/logging)

## Examples

```bash
zagent logs
zagent logs --follow
zagent logs --json
zagent logs --limit 500
```


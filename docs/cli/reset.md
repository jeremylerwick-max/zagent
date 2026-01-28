---
summary: "CLI reference for `zagent reset` (reset local state/config)"
read_when:
  - You want to wipe local state while keeping the CLI installed
  - You want a dry-run of what would be removed
---

# `zagent reset`

Reset local config/state (keeps the CLI installed).

```bash
zagent reset
zagent reset --dry-run
zagent reset --scope config+creds+sessions --yes --non-interactive
```


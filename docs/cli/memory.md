---
summary: "CLI reference for `zagent memory` (status/index/search)"
read_when:
  - You want to index or search semantic memory
  - You’re debugging memory availability or indexing
---

# `zagent memory`

Manage semantic memory indexing and search.
Provided by the active memory plugin (default: `memory-core`; set `plugins.slots.memory = "none"` to disable).

Related:
- Memory concept: [Memory](/concepts/memory)
 - Plugins: [Plugins](/plugins)

## Examples

```bash
zagent memory status
zagent memory status --deep
zagent memory status --deep --index
zagent memory status --deep --index --verbose
zagent memory index
zagent memory index --verbose
zagent memory search "release checklist"
zagent memory status --agent main
zagent memory index --agent main --verbose
```

## Options

Common:

- `--agent <id>`: scope to a single agent (default: all configured agents).
- `--verbose`: emit detailed logs during probes and indexing.

Notes:
- `memory status --deep` probes vector + embedding availability.
- `memory status --deep --index` runs a reindex if the store is dirty.
- `memory index --verbose` prints per-phase details (provider, model, sources, batch activity).

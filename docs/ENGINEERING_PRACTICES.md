# 🏗️ Software Engineering Best Practices for ZAgent
> Written for Jeremy by Claude | 2026-02-07
> These practices will save you weeks of debugging and rework.

---

## 1. VERSION CONTROL STRATEGY (Git Flow Lite)

### Branches
```
main          ← Production-ready code ONLY. Never commit directly.
├── develop   ← Integration branch. All features merge here first.
│   ├── feat/pco-core       ← Feature branch
│   ├── feat/memory-api     ← Feature branch
│   ├── fix/ollama-timeout  ← Bug fix branch
│   └── chore/lint-setup    ← Maintenance branch
```

### Rules
- **NEVER push directly to `main`** — always go through Pull Requests
- **One feature = one branch** — don't mix unrelated changes
- Branch naming: `feat/`, `fix/`, `chore/`, `docs/`, `refactor/`
- Delete branches after merging
- Pull from `develop` before starting new work: `git pull origin develop`

### Conventional Commits
Every commit message follows a format. This enables auto-changelogs.
```
feat: add PCO orchestration endpoint
fix: handle Ollama timeout gracefully  
chore: update dependencies
docs: add API documentation
refactor: simplify memory retrieval logic
test: add unit tests for verifier window
```

**Why it matters:** 6 months from now, `git log --oneline` tells you the entire project story.

---

## 2. ISSUE-DRIVEN DEVELOPMENT

### The Golden Rule
**No code without an issue. No issue without acceptance criteria.**


### Issue Template
Every issue should have:
```markdown
## Description
What needs to be built/fixed in 1-2 sentences.

## Acceptance Criteria  
- [ ] Specific, testable condition 1
- [ ] Specific, testable condition 2
- [ ] Specific, testable condition 3

## Technical Notes
Implementation hints, relevant files, API endpoints.

## Definition of Done
- [ ] Code written and working
- [ ] Tests pass
- [ ] No console errors/warnings
- [ ] PR reviewed and approved
```

**Why it matters:** When you (or Copilot, or Claude Code) pick up an issue, there's zero ambiguity. "Make the API work" is a bad issue. "POST /orchestrate returns 200 with synthesized response from 3 models within 30 seconds" is a great issue.

---

## 3. TEST-FIRST THINKING

You don't need 100% test coverage. You need tests for the **scary parts**:

### What to Test
- **API endpoints** — does /orchestrate return the right shape?
- **Data transformations** — does the synthesizer combine correctly?
- **Error paths** — what happens when Ollama is down?
- **Integration points** — does pgvector search actually return results?

### What NOT to Test
- UI layout/styling (too brittle, changes often)
- Third-party library internals
- One-liner functions

### Test File Convention
```
src/
├── orchestrator.ts       ← Source
├── orchestrator.test.ts  ← Test (colocated)
```

---

## 4. ENVIRONMENT MANAGEMENT

### .env Files
```
.env.example    ← Checked into git (template with dummy values)
.env            ← NEVER checked into git (your real secrets)
.env.test       ← Test environment config
```

### .gitignore Must-Haves
```
.env
.env.local
.env.*.local
node_modules/
dist/
*.log
.DS_Store
```

---

## 5. PR (Pull Request) DISCIPLINE

### PR Template
```markdown
## What
One-sentence summary of the change.

## Why  
Link to the GitHub issue: Closes #XX

## How
Brief technical approach.

## Testing
How to verify this works.

## Screenshots (if UI)
Before/after.
```

### PR Size Rule
- **Small PRs** (< 300 lines changed) get reviewed fast
- **Large PRs** (> 500 lines) → break it up
- Each PR should do ONE thing

---

## 6. SEMANTIC VERSIONING

```
v1.0.0
│ │ │
│ │ └── PATCH: bug fixes, no API changes
│ └──── MINOR: new features, backward compatible
└────── MAJOR: breaking changes
```

Start at `v0.1.0` during development. Bump to `v1.0.0` when you first deploy to production.

---

## 7. DOCUMENTATION AS CODE

### Required Docs
- `README.md` — How to install and run (30-second setup)
- `docs/ARCHITECTURE.md` — System design decisions
- `docs/API.md` — Every endpoint with request/response examples
- `CHANGELOG.md` — Auto-generated from conventional commits
- `CONTRIBUTING.md` — How to contribute (even if only you)

### Code Comments Philosophy
- **Don't** comment WHAT the code does (the code says that)
- **Do** comment WHY the code does something unexpected
- **Do** comment business logic that isn't obvious from code

```typescript
// BAD: Increment counter
counter++;

// GOOD: Retry up to 3x because Ollama cold-starts take ~10s on first load
for (let retry = 0; retry < 3; retry++) {
```

---

## 8. ERROR HANDLING PATTERNS

### Never Swallow Errors
```typescript
// BAD
try { doThing() } catch(e) { /* ignore */ }

// GOOD  
try { doThing() } catch(e) {
  logger.error('doThing failed', { error: e.message, context });
  throw new AppError('ORCHESTRATION_FAILED', e);
}
```

### Fail Fast, Fail Loud
- Validate inputs at the boundary (API endpoints)
- Use typed errors with error codes
- Return meaningful error messages to the client

---

## 9. PROJECT STRUCTURE

```
zagent/
├── src/                    # All source code
│   ├── api/                # REST endpoints
│   ├── core/               # Business logic (orchestrator, synthesizer)
│   ├── models/             # Data models/types
│   ├── services/           # External integrations (Ollama, pgvector)
│   ├── utils/              # Shared utilities
│   └── config/             # Configuration loading
├── tests/                  # Test files
├── docs/                   # Documentation
├── scripts/                # Build/deploy scripts
├── .github/                # CI/CD, issue templates, PR templates
│   ├── workflows/          # GitHub Actions
│   └── ISSUE_TEMPLATE/     # Issue templates
└── docker/                 # Docker configs
```

---

## 10. THE MOST IMPORTANT RULE

**Make it work → Make it right → Make it fast**

1. **Work**: Get the feature functional with ugly code. Ship it.
2. **Right**: Refactor, add tests, clean up. PR review.
3. **Fast**: Profile, optimize bottlenecks. Only if needed.

Most projects die at step 1 trying to be perfect. Ship first.

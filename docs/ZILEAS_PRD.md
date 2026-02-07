
### Phase 0: Make the Fork Work (Week 1)
> Goal: OpenClaw runs locally with Ollama, stripped of stuff we don't need.

| # | Issue Title | Priority |
|---|------------|----------|
| 1 | Strip unused channel integrations (WhatsApp, Telegram, Discord, iMessage, Signal, LINE) | P0 |
| 2 | Strip browser automation, TTS, canvas, pairing, plugin-sdk | P0 |
| 3 | Configure Ollama as default/only provider | P0 |
| 4 | Verify gateway starts and web UI loads | P0 |
| 5 | Verify Slack channel works with local Ollama model | P0 |
| 6 | Rename branding: OpenClaw → Zileas throughout | P1 |

**Exit criteria:** Send a Slack message, get a response from a local Ollama model, see it in the web dashboard.

### Phase 1: Multi-Model Orchestration (Week 2-3)
> Goal: Multiple models work together on queries.

| # | Issue Title | Priority |
|---|------------|----------|
| 7 | Model registry: track loaded models, RAM usage, status | P0 |
| 8 | Task router: classify query type → assign best model | P0 |
| 9 | Parallel execution: run 2-3 models simultaneously | P0 |
| 10 | Synthesizer: merge parallel outputs into single response | P0 |
| 11 | Confidence scoring and model agreement display | P1 |
| 12 | Model health monitoring in web dashboard | P1 |
| 13 | Sequential fallback when RAM is tight (can't load all models) | P1 |

**Exit criteria:** Ask a coding question, see Qwen + Mistral + Scout process it, get synthesized answer.

### Phase 2: Memory Integration (Week 4-5)
> Goal: Zileas remembers everything across sessions.

| # | Issue Title | Priority |
|---|------------|----------|
| 14 | Connect to existing pgvector DB (34.28.163.109) | P0 |
| 15 | Memory search: semantic search over organized_memories | P0 |
| 16 | Memory injection: auto-add relevant memories to prompts | P0 |
| 17 | Auto-extract: pull facts from conversations → store | P1 |
| 18 | Memory UI panel in web dashboard | P1 |
| 19 | Scout organizer integration (batch process via cron) | P2 |

**Exit criteria:** Start a conversation, Zileas automatically knows about your projects, preferences, and history.

### Phase 3: Business Automation (Week 6-7)
> Goal: Zileas can run your business tasks.

| # | Issue Title | Priority |
|---|------------|----------|
| 20 | Cron job system: schedule recurring tasks | P0 |
| 21 | Hook system: trigger actions on events | P0 |
| 22 | Script runner: execute user-defined Python/bash scripts | P0 |
| 23 | Approval gates: pause and ask before risky actions | P0 |
| 24 | Task history and audit log | P1 |
| 25 | Slack notifications for task results | P1 |

**Exit criteria:** Schedule EnabledSync to run daily, get Slack notification with results, review in dashboard.

### Phase 4: Polish (Week 8)
> Goal: Reliable, monitorable, documented.

| # | Issue Title | Priority |
|---|------------|----------|
| 26 | Structured logging with log levels and rotation | P0 |
| 27 | Error recovery: auto-restart on crash | P0 |
| 28 | Resource monitoring: RAM, GPU, model status dashboard | P1 |
| 29 | One-command setup script | P1 |
| 30 | README + quick start docs | P0 |

**Exit criteria:** Zileas runs 24/7 on Mac Studio without babysitting.

---

## NON-FUNCTIONAL REQUIREMENTS

| Requirement | Target |
|-------------|--------|
| Single-model response | < 5 seconds |
| Multi-model orchestrated response | < 30 seconds |
| Memory search | < 200ms |
| Uptime | 99% (local daemon, auto-restart) |
| Data privacy | 100% local inference, no external API calls |
| Cost per query | $0 |
| Max concurrent users | 1-3 |

---

## RISKS

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Ollama OOM with 4 models | High | Crash | Sequential fallback, model unload/reload |
| Upstream OpenClaw breaks our fork | Medium | Update pain | Minimize upstream dependency, pin version |
| Scope creep | High | Never ships | 30 issues, that's it. No feature adds until v1.0 |
| Slack API changes | Low | Channel breaks | Bolt SDK handles most of this |

---

## ARCHITECTURE (Simplified)

```
                    Slack
                      │
                      ▼
              ┌───────────────┐
              │   Gateway     │ ← HTTP API + WebSocket
              │  (Express)    │ ← Web Dashboard UI
              └───────┬───────┘
                      │
              ┌───────▼───────┐
              │   Router      │ ← Classify query → pick models
              └───────┬───────┘
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
    ┌─────────┐ ┌─────────┐ ┌─────────┐
    │ Mistral │ │  Qwen   │ │  Scout  │  ← Ollama (localhost:11434)
    │ 123B    │ │ Coder   │ │ 10M ctx │
    └────┬────┘ └────┬────┘ └────┬────┘
         └────────────┼────────────┘
                      ▼
              ┌───────────────┐
              │  Synthesizer  │ ← Merge + confidence score
              └───────┬───────┘
                      │
              ┌───────▼───────┐
              │   Memory      │ ← pgvector (GCP)
              │  + Scout Org  │ ← organized_memories table
              └───────────────┘
```

---

## SUCCESS CRITERIA FOR v1.0

- [ ] Zileas runs 24/7 on Mac Studio
- [ ] Slack messages get AI responses from local models
- [ ] Multi-model orchestration works on complex queries
- [ ] Memory persists and auto-injects into conversations
- [ ] Cron tasks run (e.g. EnabledSync daily)
- [ ] Web dashboard shows status, chat, memory
- [ ] Zero API costs

---

## OPEN QUESTIONS

1. Do we keep the existing OpenClaw gateway code or rewrite simpler?
2. Redis for task queue or in-memory (simpler)?
3. Should memory injection be automatic or opt-in per conversation?

---

*30 issues. 8 weeks. Ship it.*
</content>
<parameter name="mode">append
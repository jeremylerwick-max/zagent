# ZAgent — Product Requirements Document (PRD)
> Version: 0.1.0 | Author: Jeremy Lerwick | Date: 2026-02-07
> Status: DRAFT → Review → Approved

---

## 1. VISION

**ZAgent is a local-first AI agent platform that orchestrates multiple LLMs in parallel to complete complex tasks with verification, memory, and tool access.**

Think of it as "Claude Desktop on steroids" — but running entirely on your Mac Studio with no API costs, combining the strengths of 4+ specialized models (Scout for context, Mistral for reasoning, Qwen for coding, DeepSeek for deep analysis) through a unified orchestration layer.

### What Makes ZAgent Different
| Feature | Claude Desktop | ChatGPT | ZAgent |
|---------|---------------|---------|--------|
| Local inference | ❌ | ❌ | ✅ 405B+ on Mac Studio |
| Multi-model orchestration | ❌ | ❌ | ✅ 4 models in parallel |
| Persistent memory | Limited | Limited | ✅ pgvector + Scout |
| MCP tool access | ✅ | ❌ | ✅ Full MCP ecosystem |
| Custom skills | ❌ | GPTs | ✅ Skill files + hot reload |
| Cost per query | $0.01-$0.15 | $0.01-$0.05 | $0 (electricity only) |
| Privacy | Cloud | Cloud | 100% local |

---

## 2. TARGET USER

**Primary:** Jeremy Lerwick (dogfooding)
**Secondary:** Power users running local LLMs who want agent capabilities
**Tertiary:** Ziloss Technologies customers (future SaaS offering)

---

## 3. CORE ARCHITECTURE

```
┌──────────────────────────────────────────────────────────────┐
│                        ZAgent Platform                        │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Web UI     │  │   CLI       │  │   MCP Server        │  │
│  │  (React)     │  │  (zagent)   │  │  (Claude Desktop)   │  │
│  └──────┬───────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         └──────────────────┼───────────────────┘              │
│                            ▼                                  │
│              ┌──────────────────────────┐                     │
│              │    API Gateway (FastAPI)  │                     │
│              │    /orchestrate           │                     │
│              │    /memory                │                     │
│              │    /skills                │                     │
│              │    /tasks                 │                     │
│              └────────────┬─────────────┘                     │
│                           ▼                                   │
│              ┌──────────────────────────┐                     │
│              │  PCO (Orchestrator Core) │                     │
│              │                          │                     │
│              │  ┌────────┐ ┌────────┐   │                     │
│              │  │Verifier│ │ Coder  │   │                     │
│              │  │Mistral │ │ Qwen   │   │                     │
│              │  └────────┘ └────────┘   │                     │
│              │  ┌────────┐ ┌────────┐   │                     │
│              │  │Reasoner│ │Synth   │   │                     │
│              │  │DeepSeek│ │ Scout  │   │                     │
│              │  └────────┘ └────────┘   │                     │
│              └────────────┬─────────────┘                     │
│                           ▼                                   │
│         ┌─────────────────────────────────────┐               │
│         │           Service Layer              │               │
│         │  ┌────────┐ ┌────────┐ ┌──────────┐ │               │
│         │  │ Ollama  │ │pgvector│ │  Tools   │ │               │
│         │  │ Client  │ │ Memory │ │ Registry │ │               │
│         │  └────────┘ └────────┘ └──────────┘ │               │
│         └─────────────────────────────────────┘               │
└──────────────────────────────────────────────────────────────┘
```


## 4. TECH STACK

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| Frontend | React + TailwindCSS + Vite | Fast, modern, already in OpenClaw fork |
| API | FastAPI (Python) | Async, fast, great for AI workloads |
| Orchestrator | Python + asyncio | Native async for parallel model calls |
| LLM Interface | Ollama HTTP API | Local models, no API keys |
| Memory | PostgreSQL + pgvector | Already deployed on GCP |
| Embeddings | nomic-embed-text (768d) | Fast, local, good quality |
| Task Queue | Redis (future) | For background task processing |
| Auth | JWT + API keys | Simple, stateless |
| Deploy | Docker + docker-compose | One command to run everything |

### Models (on Mac Studio 512GB)
| Role | Model | Size | Purpose |
|------|-------|------|---------|
| Verifier | mistral-large:123b | 73GB | Validation, QA, review |
| Coder | qwen2.5-coder:32b | 19GB | Code generation, debugging |
| Reasoner | deepseek-r1:32b | 19GB | Deep analysis, planning |
| Synthesizer | llama4:scout | 67GB | 10M context, final synthesis |
| Fast Response | mistral:7b | 4.4GB | Quick queries, triage |
| Embeddings | nomic-embed-text | 274MB | Vector embeddings |

---

## 5. FEATURE BREAKDOWN

### Phase 0: Foundation (Week 1-2) 🏗️
> Get the basics working end-to-end

| # | Feature | Priority | Issue |
|---|---------|----------|-------|
| F0.1 | Project setup: clean fork, develop branch, CI | P0 | #1 |
| F0.2 | FastAPI skeleton with health check endpoint | P0 | #2 |
| F0.3 | Ollama client service (connect, list models, generate) | P0 | #3 |
| F0.4 | Single-model chat endpoint (POST /chat) | P0 | #4 |
| F0.5 | Basic React UI: chat interface with streaming | P0 | #5 |
| F0.6 | Docker Compose: API + UI + Ollama | P1 | #6 |

**Exit Criteria:** Can send a message via UI, get a streamed response from one local model.

### Phase 1: PCO Core (Week 3-4) 🧠
> The parallel orchestration engine

| # | Feature | Priority | Issue |
|---|---------|----------|-------|
| F1.1 | Window abstraction: VerifierWindow, CoderWindow, etc. | P0 | #7 |
| F1.2 | Parallel execution engine (asyncio.gather) | P0 | #8 |
| F1.3 | Task router: classify query → assign models | P0 | #9 |
| F1.4 | Synthesizer: merge parallel outputs into one response | P0 | #10 |
| F1.5 | POST /orchestrate endpoint with PCO pipeline | P0 | #11 |
| F1.6 | Consensus/voting on conflicting outputs | P1 | #12 |
| F1.7 | Streaming from multiple models to UI | P1 | #13 |

**Exit Criteria:** Send a coding question, see all 4 models process in parallel, get a synthesized answer.

### Phase 2: Memory System (Week 5-6) 🧬
> Persistent knowledge across sessions

| # | Feature | Priority | Issue |
|---|---------|----------|-------|
| F2.1 | pgvector connection service | P0 | #14 |
| F2.2 | Memory CRUD: store, search, update, delete | P0 | #15 |
| F2.3 | Auto-memory: extract facts from conversations | P1 | #16 |
| F2.4 | Memory injection: relevant memories added to prompts | P0 | #17 |
| F2.5 | Memory UI: browse, search, edit stored memories | P1 | #18 |
| F2.6 | Scout batch organizer integration (from persistent-memory repo) | P2 | #19 |

**Exit Criteria:** Conversations produce memories. Starting a new chat auto-injects relevant context.

### Phase 3: Tool System (Week 7-8) 🔧
> MCP-compatible tool execution

| # | Feature | Priority | Issue |
|---|---------|----------|-------|
| F3.1 | Tool registry: register, discover, describe tools | P0 | #20 |
| F3.2 | Built-in tools: filesystem, web search, calculator | P0 | #21 |
| F3.3 | MCP server compatibility layer | P1 | #22 |
| F3.4 | Tool calling: model decides when to use tools | P0 | #23 |
| F3.5 | Tool result injection back into conversation | P0 | #24 |
| F3.6 | Sandbox mode: restricted tool access per session | P2 | #25 |

**Exit Criteria:** Ask "what files are in my Desktop?" and get an actual filesystem listing.

### Phase 4: Skills & Agents (Week 9-10) 🤖
> Reusable skill packs and autonomous task chains

| # | Feature | Priority | Issue |
|---|---------|----------|-------|
| F4.1 | Skill file format: YAML/MD with system prompt + tools | P0 | #26 |
| F4.2 | Skill hot-reload: edit file, auto-register | P1 | #27 |
| F4.3 | Built-in skills: code review, web research, data analysis | P1 | #28 |
| F4.4 | Task chains: multi-step autonomous execution | P1 | #29 |
| F4.5 | Human-in-the-loop: pause for approval on risky steps | P0 | #30 |
| F4.6 | Task history and audit log | P1 | #31 |

**Exit Criteria:** Define a "code review" skill, trigger it on a file, get a multi-step analysis with approval gates.

### Phase 5: Polish & Deploy (Week 11-12) ✨
> Production-ready

| # | Feature | Priority | Issue |
|---|---------|----------|-------|
| F5.1 | Auth: API keys + JWT for UI | P0 | #32 |
| F5.2 | Rate limiting and resource management | P1 | #33 |
| F5.3 | Observability: structured logging, metrics | P1 | #34 |
| F5.4 | Model health monitoring dashboard | P1 | #35 |
| F5.5 | One-command setup script (install deps, pull models) | P0 | #36 |
| F5.6 | Documentation: README, API docs, quick start | P0 | #37 |

**Exit Criteria:** Someone can clone the repo, run one command, and have the full platform running.


---

## 6. UI SPECIFICATION

### 6.1 Main Chat View
```
┌──────────────────────────────────────────────────────────────┐
│  ZAgent                          [Memory] [Skills] [⚙ Settings]│
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ You: How do I fix the EnabledSync store mapping bug?      ││
│  └──────────────────────────────────────────────────────────┘│
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ ZAgent: [Orchestrating with 3 models...]                  ││
│  │                                                            ││
│  │ ┌─────────┐ ┌─────────┐ ┌─────────┐                      ││
│  │ │Verifier │ │ Coder   │ │Reasoner │  ← Live model status  ││
│  │ │✅ Done   │ │⏳ 3.2s  │ │✅ Done   │                      ││
│  │ └─────────┘ └─────────┘ └─────────┘                      ││
│  │                                                            ││
│  │ **Synthesized Answer:**                                    ││
│  │ The store mapping bug is caused by... [full answer]        ││
│  │                                                            ││
│  │ **Confidence: 94%** | Models agreed: 3/3                  ││
│  └──────────────────────────────────────────────────────────┘│
│                                                               │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ Type a message...                    [Skill ▼] [Send →]   ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

### 6.2 Memory Panel (Slide-out)
```
┌────────────────────────────┐
│ 🧬 Memory                  │
│ Search: [____________]     │
│                            │
│ ┌────────────────────────┐ │
│ │ 📁 project (18)        │ │
│ │ ├ Ziloss CRM [imp:10]  │ │
│ │ ├ EnabledSync [imp:9]   │ │
│ │ ├ CHS Telehealth [8]   │ │
│ │                         │ │
│ │ 📁 fact (16)            │ │
│ │ ├ Stock Portfolio [8]   │ │
│ │ ├ Trading Strategy [7]  │ │
│ │                         │ │
│ │ 📁 person (1)           │ │
│ │ ├ Jeremy [5]            │ │
│ └────────────────────────┘ │
│                            │
│ [+ Add Memory] [🔄 Re-org] │
└────────────────────────────┘
```

### 6.3 Skills Panel
```
┌────────────────────────────┐
│ 🔧 Skills                  │
│                            │
│ ┌ Active ──────────────┐   │
│ │ ✅ Code Review        │   │
│ │ ✅ Web Research        │   │
│ │ ✅ Data Analysis       │   │
│ └──────────────────────┘   │
│                            │
│ ┌ Available ───────────┐   │
│ │ ○ Lead Generation     │   │
│ │ ○ Email Drafting      │   │
│ │ ○ CRM Automation      │   │
│ └──────────────────────┘   │
│                            │
│ [+ New Skill] [📁 Import]  │
└────────────────────────────┘
```

### 6.4 Model Status Bar (Bottom)
```
┌──────────────────────────────────────────────────────────────┐
│ 🟢 Mistral:123B (72GB) | 🟢 Qwen:32B (19GB) | 🟡 Scout (loading) │
│ RAM: 340/512 GB | GPU: 62% | Queue: 0                        │
└──────────────────────────────────────────────────────────────┘
```

---

## 7. API SPECIFICATION

### Core Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /chat | Single-model chat (fast) |
| POST | /orchestrate | Multi-model PCO pipeline |
| GET | /models | List available Ollama models |
| GET | /models/{name}/status | Model health/memory usage |
| GET | /memory/search?q= | Semantic memory search |
| POST | /memory | Store a memory |
| PUT | /memory/{id} | Update a memory |
| DELETE | /memory/{id} | Delete a memory |
| GET | /skills | List registered skills |
| POST | /skills/{name}/run | Execute a skill |
| POST | /tasks | Create a multi-step task |
| GET | /tasks/{id} | Get task status |
| POST | /tasks/{id}/approve | Approve pending step |
| GET | /health | System health check |
| GET | /metrics | Prometheus metrics |

### Request/Response: POST /orchestrate
```json
// Request
{
  "message": "Fix the store mapping bug in enabledsync_v8.py",
  "context": {
    "files": ["/path/to/enabledsync_v8.py"],
    "memory_search": true,
    "skill": "code-review"
  },
  "models": ["verifier", "coder", "reasoner"],
  "stream": true
}

// Response (streamed SSE)
event: model_start
data: {"model": "verifier", "status": "running"}

event: model_start  
data: {"model": "coder", "status": "running"}

event: model_complete
data: {"model": "verifier", "output": "...", "time_ms": 3200}

event: model_complete
data: {"model": "coder", "output": "...", "time_ms": 5100}

event: synthesis
data: {"output": "...", "confidence": 0.94, "agreement": "3/3"}

event: done
data: {"total_time_ms": 6200, "models_used": 3}
```

---

## 8. NON-FUNCTIONAL REQUIREMENTS

| Requirement | Target |
|-------------|--------|
| Single-model response time | < 5 seconds |
| Orchestrated response time | < 30 seconds |
| Memory search latency | < 200ms |
| Concurrent users | 1-3 (local use) |
| Uptime | Best effort (local daemon) |
| Data privacy | 100% local, no external calls |
| Max context per model | 128K (Mistral), 10M (Scout) |

---

## 9. RISKS & MITIGATIONS

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Ollama OOM with 4 models loaded | High | Models crash | Sequential fallback, model unload/reload |
| Scout cold start slow (67GB) | Medium | 30s+ first query | Keep warm, preload on boot |
| Parallel models disagree | Medium | Confusing output | Confidence scoring, majority vote |
| OpenClaw upstream breaks fork | Low | Update conflicts | Minimal upstream dependency |
| Scope creep | High | Never ships | Phase gates, MVP first |

---

## 10. SUCCESS METRICS

| Metric | Phase 0 | Phase 2 | Phase 5 |
|--------|---------|---------|---------|
| End-to-end response | Working | < 15s | < 10s |
| Organized memories | 42 | 200+ | 500+ |
| Available skills | 0 | 3 | 10+ |
| Daily active use | Testing | Dogfooding | Primary tool |
| Cost per query | $0 | $0 | $0 |

---

## 11. OPEN QUESTIONS

1. Should we keep the OpenClaw UI or build custom React from scratch?
2. Redis for task queue or start with in-memory?
3. Should skills be YAML, Markdown, or Python files?
4. How to handle model scheduling when RAM is tight?
5. Should the MCP server be built into ZAgent or separate?

---

*This PRD is a living document. Update as decisions are made.*
*Next step: Create GitHub Issues from Phase 0 features.*

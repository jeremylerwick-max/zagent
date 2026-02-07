# Zileas UI Specification
> Version: 0.1.0 | Date: 2026-02-07

---

## Design Philosophy

1. **One brain illusion** — 4 models work together but user sees one response
2. **Progressive disclosure** — clean by default, details on demand
3. **Claude-inspired layout** — chat left, activity right
4. **Smooth not choppy** — streaming tokens, CSS transitions, skeleton loaders

---

## Layout: Two-Panel Split

```
┌─────────────────────────────────────────────────────────────────────┐
│  Zileas                                        [⚙] [🔌 MCP]       │
├────────────────────────────────┬────────────────────────────────────┤
│                                │                                    │
│  CHAT PANEL (60%)              │  ACTIVITY PANEL (40%)              │
│                                │                                    │
│  Conversation lives here.      │  Shows what's happening            │
│  Clean. No model names.        │  behind the scenes.                │
│  One voice. One response.      │                                    │
│                                │  Collapsible. Can be hidden.       │
│                                │  Tabs at top for different views.  │
│                                │                                    │
├────────────────────────────────┤                                    │
│  [/ commands] Type here...  [→]│                                    │
└────────────────────────────────┴────────────────────────────────────┘
```

### Chat Panel (Left, 60%)
- Messages flow vertically, user on right, Zileas on left
- Zileas responses stream token-by-token with smooth animation
- NO model names visible in responses (synthesized = one voice)
- Subtle confidence badge after response: "94% · 3 models agreed"
  - Click badge to expand model breakdown in right panel
- Markdown rendering for code blocks, lists, etc.
- Input bar at bottom:
  - Text input with auto-grow (up to 6 lines)
  - "/" triggers slash command menu (floating above input)
  - Send button (or Enter)
  - No other buttons. No file upload (v1). No dropdowns.

### Activity Panel (Right, 40%)
- Can be collapsed to give chat full width (toggle via drag or button)
- 4 tabs across the top:

```
[ Models ] [ Preview ] [ Memory ] [ Tools ]
```

**Tab 1: Models (default)** — What the LLMs are doing RIGHT NOW
```
┌─────────────────────────────────┐
│  Models                         │
│                                 │
│  ┌───────────────────────────┐  │
│  │ 🟢 Scout (Synthesizer)    │  │
│  │ Merging 3 responses...    │  │
│  │ ████████░░ 80%            │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │ ✅ Mistral 123B (Verifier)│  │
│  │ Done · 3.2s · 847 tokens  │  │
│  │ ▸ View output             │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │ ✅ Qwen 32B (Coder)       │  │
│  │ Done · 5.1s · 1,204 tokens│  │
│  │ ▸ View output             │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │ ⏳ DeepSeek (Reasoner)    │  │
│  │ Generating... 2.8s        │  │
│  │ ████████████░░░ 85%       │  │
│  └───────────────────────────┘  │
│                                 │
│  ─── System ────────────────    │
│  RAM: 340/512 GB                │
│  GPU: 62%                       │
│  Queue: 0                       │
└─────────────────────────────────┘
```

- Each model card: status icon, role name, timing, token count
- "View output" expands to show that model's raw response
- When idle: shows loaded models and RAM usage only
- Animate cards appearing when orchestration starts

**Tab 2: Preview** — Code and file previews (like Claude artifacts)
```
┌─────────────────────────────────┐
│  Preview                        │
│  ┌───────────────────────────┐  │
│  │ enabledsync_v8.py     [⤓] │  │
│  │                            │  │
│  │ def search_lead(phone):    │  │
│  │     url = f"{BASE}/Search" │  │
│  │     resp = session.post(   │  │
│  │         url,               │  │
│  │         json={"text": ph...│  │
│  │     )                      │  │
│  │                            │  │
│  └───────────────────────────┘  │
│                                 │
│  No other previews              │
└─────────────────────────────────┘
```

- Code blocks from responses render here as full previews
- Syntax highlighting, line numbers
- Copy button, download button
- Multiple files stack vertically
- Click a code block in chat → jumps to preview tab

**Tab 3: Memory** — What context was injected
```
┌─────────────────────────────────┐
│  Memory                [Search] │
│                                 │
│  Injected for this message:     │
│  ┌───────────────────────────┐  │
│  │ 📁 project · imp:10       │  │
│  │ Ziloss CRM — Master plan  │  │
│  │ for agency-focused CRM... │  │
│  │ Similarity: 0.91          │  │
│  └───────────────────────────┘  │
│  ┌───────────────────────────┐  │
│  │ 📁 config · imp:7         │  │
│  │ Claude Skills library at  │  │
│  │ ~/Desktop/claude-skills/  │  │
│  │ Similarity: 0.78          │  │
│  └───────────────────────────┘  │
│                                 │
│  Total memories: 42             │
│  Injected: 2 · Threshold: 0.7  │
└─────────────────────────────────┘
```

- Shows which memories were auto-injected for current message
- Similarity scores visible
- Search box to manually query memory
- Click memory to see full detail

**Tab 4: Tools** — MCP and tool execution
```
┌─────────────────────────────────┐
│  Tools                          │
│                                 │
│  Active MCP Servers:            │
│  ┌───────────────────────────┐  │
│  │ 🟢 Filesystem     12 tok  │  │
│  │ 🟢 Desktop Cmd    45 tok  │  │
│  │ ⚪ Ollama MCP   disabled  │  │
│  └───────────────────────────┘  │
│                                 │
│  Recent tool calls:             │
│  ▸ read_file(/home/...) 0.2s   │
│  ▸ list_dir(/Desktop) 0.1s     │
│                                 │
└─────────────────────────────────┘
```

- Token count per MCP server this session
- Toggle switch to enable/disable each server live
- Recent tool calls with timing
- Expand tool call to see input/output

---

## Settings (⚙ gear icon → slide-out or modal)

```
┌──────────────────────────────────┐
│  Settings                    [×] │
│                                  │
│  ── Models ──────────────────    │
│  Default model: [mistral:7b ▼]  │
│  Orchestration: [On/Off]        │
│  Models for orchestration:       │
│    ☑ Mistral 123B (Verifier)    │
│    ☑ Qwen 32B (Coder)          │
│    ☑ Scout (Synthesizer)        │
│    ☐ DeepSeek (Reasoner)        │
│                                  │
│  ── Memory ──────────────────    │
│  Auto-inject: [On/Off]          │
│  Similarity threshold: [0.7]    │
│  Max memories per query: [5]    │
│                                  │
│  ── MCP Servers ─────────────    │
│  🟢 Filesystem         [On/Off] │
│  🟢 Desktop Commander  [On/Off] │
│  ⚪ Ollama MCP         [On/Off] │
│  [+ Add MCP Server]             │
│                                  │
│  ── System ──────────────────    │
│  Log level: [info ▼]            │
│  Theme: [Dark/Light]            │
│  Activity panel: [Show/Hide]    │
│                                  │
└──────────────────────────────────┘
```

---

## MCP Server Management (🔌 icon)

Quick-access panel just for MCP servers. Separate from settings
because you toggle these mid-conversation.

```
┌──────────────────────────────────┐
│  MCP Servers                 [×] │
│                                  │
│  Server            Tokens  State │
│  ─────────────────────────────── │
│  Filesystem          12   [🟢]  │
│  Desktop Cmd         45   [🟢]  │
│  Ollama MCP           0   [⚪]  │
│  Google Drive         0   [⚪]  │
│  ─────────────────────────────── │
│  Total context: 57 tokens        │
│                                  │
│  [+ Add Server]                  │
└──────────────────────────────────┘
```

- Token count = how much context each server is consuming
- One-click toggle on/off
- Red highlight if a server is consuming > 1000 tokens (context hog warning)

---

## Slash Commands (v1)

Type "/" in input to see floating menu:

```
┌──────────────────────┐
│ /models  List models │
│ /memory  Search mem  │
│ /clear   New chat    │
│ /status  System info │
│ /help    Show help   │
└──────────────────────┘
```

- Fuzzy match as you type: "/mo" shows /models
- Results appear inline in chat (not in activity panel)
- Minimal set for v1, expand later

---

## Animations & Polish

| Element | Animation |
|---------|-----------|
| Token streaming | Fade-in per token, 30ms delay |
| Model cards | Slide-in from right when orchestration starts |
| Activity panel | Smooth resize with drag handle |
| Slash menu | Fade-up from input bar |
| Settings | Slide-in from right edge |
| Confidence badge | Fade-in after response completes |
| MCP toggle | Smooth switch with status color transition |
| Error states | Gentle red pulse, not harsh flash |

---

## Color Palette (Dark Theme Default)

| Element | Color |
|---------|-------|
| Background | #0f0f0f (near black) |
| Chat area | #1a1a1a |
| Activity panel | #141414 |
| User message bubble | #2a2a2a |
| Zileas message | No bubble, flat on background |
| Accent (links, buttons) | #7c5cfc (purple, Ziloss brand) |
| Success | #22c55e |
| Warning | #eab308 |
| Error | #ef4444 |
| Text primary | #e5e5e5 |
| Text secondary | #888888 |

---

## Responsive Behavior

| Width | Layout |
|-------|--------|
| > 1200px | Two-panel (60/40 split) |
| 900-1200px | Two-panel (70/30 split) |
| < 900px | Chat only, activity panel as overlay/drawer |

---

## What We Are NOT Building (v1)

- File upload / drag-and-drop
- Voice input/output
- Multiple conversation threads (single chat for now)
- User accounts / auth (local use only)
- Mobile-optimized layout
- Custom themes
- Keyboard shortcuts beyond slash commands

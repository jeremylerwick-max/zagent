/**
 * Zileas Tier Definitions
 * Maps each difficulty tier to its model lineup
 */

import type { TierConfig, ModelRef } from "./types.js";

// ── Local models (free) ──────────────────────────────────────
const QWEN_CODER: ModelRef = {
  provider: "ollama",
  model: "qwen2.5-coder:32b",
  role: "primary",
  contextWindow: 32768,
};
const MISTRAL_LARGE: ModelRef = {
  provider: "ollama",
  model: "mistral-large:123b",
  role: "primary",
  contextWindow: 131072,
};
const DEEPSEEK_R1: ModelRef = {
  provider: "ollama",
  model: "deepseek-r1:32b",
  role: "primary",
  contextWindow: 65536,
};
const SCOUT: ModelRef = {
  provider: "ollama",
  model: "llama4:scout",
  role: "primary",
  contextWindow: 10_000_000,
};

// ── API models (paid) ────────────────────────────────────────
const CLAUDE_SONNET: ModelRef = {
  provider: "anthropic",
  model: "claude-sonnet-4-5-20250929",
  role: "fallback",
  contextWindow: 200_000,
  costPer1kInput: 0.003,
  costPer1kOutput: 0.015,
};
const GPT4O: ModelRef = {
  provider: "openai",
  model: "gpt-4o",
  role: "fallback",
  contextWindow: 128_000,
  costPer1kInput: 0.0025,
  costPer1kOutput: 0.01,
};
const GEMINI_PRO: ModelRef = {
  provider: "google",
  model: "gemini-2.5-pro",
  role: "fallback",
  contextWindow: 1_000_000,
  costPer1kInput: 0.00125,
  costPer1kOutput: 0.01,
};
const CLAUDE_OPUS: ModelRef = {
  provider: "anthropic",
  model: "claude-opus-4-5-20250929",
  role: "fallback",
  contextWindow: 200_000,
  costPer1kInput: 0.015,
  costPer1kOutput: 0.075,
};

// ── Tier definitions ─────────────────────────────────────────
export const TIER_CONFIGS: Record<string, TierConfig> = {
  elementary: {
    tier: "elementary",
    label: "⚡ Quick",
    description: "Simple factual, greetings, math, short answers",
    maxTokens: 1024,
    models: [QWEN_CODER, CLAUDE_SONNET],
  },
  "high-school": {
    tier: "high-school",
    label: "📝 Standard",
    description: "Explain, summarize, write, translate",
    maxTokens: 4096,
    models: [QWEN_CODER, CLAUDE_SONNET],
  },
  college: {
    tier: "college",
    label: "🔧 Technical",
    description: "Code, debug, multi-step reasoning, analysis",
    maxTokens: 8192,
    models: [QWEN_CODER, MISTRAL_LARGE, CLAUDE_SONNET, GPT4O],
  },
  masters: {
    tier: "masters",
    label: "🏗️ Complex",
    description: "Architecture, long input, multi-file, research",
    maxTokens: 16384,
    models: [MISTRAL_LARGE, SCOUT, CLAUDE_SONNET, GEMINI_PRO],
  },
  phd: {
    tier: "phd",
    label: "🧠 Expert",
    description: "High stakes, low confidence, orchestrated multi-model",
    maxTokens: 32768,
    models: [MISTRAL_LARGE, DEEPSEEK_R1, SCOUT, CLAUDE_OPUS, GEMINI_PRO],
  },
};

export { QWEN_CODER, MISTRAL_LARGE, DEEPSEEK_R1, SCOUT };
export { CLAUDE_SONNET, GPT4O, GEMINI_PRO, CLAUDE_OPUS };

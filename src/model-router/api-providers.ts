/**
 * Zileas API Provider Manager
 * Z-33: Manage API fallback providers + spend tracking
 */

import type { ModelRef, SpendTracker, RouterConfig } from "./types.js";

// ── Provider endpoints ───────────────────────────────────────

const PROVIDER_ENDPOINTS: Record<string, string> = {
  anthropic: "https://api.anthropic.com/v1/messages",
  openai: "https://api.openai.com/v1/chat/completions",
  google: "https://generativelanguage.googleapis.com/v1beta/models",
  openrouter: "https://openrouter.ai/api/v1/chat/completions",
  ollama: "http://127.0.0.1:11434/v1/chat/completions",
};

// ── Spend tracker ────────────────────────────────────────────

let spendState: SpendTracker = {
  daily: 0,
  monthly: 0,
  dailyLimit: 5.0, // $5/day default
  monthlyLimit: 50.0, // $50/month default
  lastReset: new Date().toISOString().split("T")[0],
};

export function getSpend(): SpendTracker {
  maybeResetSpend();
  return { ...spendState };
}

export function recordSpend(cost: number): void {
  maybeResetSpend();
  spendState.daily += cost;
  spendState.monthly += cost;
}

export function setSpendLimits(daily: number, monthly: number): void {
  spendState.dailyLimit = daily;
  spendState.monthlyLimit = monthly;
}

export function canSpend(estimatedCost: number): boolean {
  maybeResetSpend();
  if (spendState.daily + estimatedCost > spendState.dailyLimit) return false;
  if (spendState.monthly + estimatedCost > spendState.monthlyLimit) return false;
  return true;
}

function maybeResetSpend(): void {
  const today = new Date().toISOString().split("T")[0];
  if (spendState.lastReset !== today) {
    spendState.daily = 0;
    // Monthly reset on 1st
    if (new Date().getDate() === 1) {
      spendState.monthly = 0;
    }
    spendState.lastReset = today;
  }
}

// ── Cost estimation ──────────────────────────────────────────

export function estimateCost(model: ModelRef, inputTokens: number, outputTokens: number): number {
  const inCost = (model.costPer1kInput ?? 0) * (inputTokens / 1000);
  const outCost = (model.costPer1kOutput ?? 0) * (outputTokens / 1000);
  return Math.round((inCost + outCost) * 10000) / 10000; // 4 decimal precision
}

// ── Provider availability check ──────────────────────────────

const apiKeyCache: Record<string, string | undefined> = {};

export function setApiKey(provider: string, key: string): void {
  apiKeyCache[provider] = key;
}

export function getApiKey(provider: string): string | undefined {
  // Check cache first, then env
  if (apiKeyCache[provider]) return apiKeyCache[provider];

  const envMap: Record<string, string> = {
    anthropic: "ANTHROPIC_API_KEY",
    openai: "OPENAI_API_KEY",
    google: "GEMINI_API_KEY",
    openrouter: "OPENROUTER_API_KEY",
  };
  const envKey = envMap[provider];
  if (envKey && process.env[envKey]) {
    apiKeyCache[provider] = process.env[envKey];
    return apiKeyCache[provider];
  }
  return undefined;
}

export function isProviderAvailable(provider: string): boolean {
  if (provider === "ollama") return true; // always available locally
  return !!getApiKey(provider);
}

export function getEndpoint(provider: string): string {
  return PROVIDER_ENDPOINTS[provider] ?? PROVIDER_ENDPOINTS.openrouter;
}

// ── Fallback chain resolution ────────────────────────────────

export function resolveFallbackChain(
  models: ModelRef[],
  estimatedInputTokens: number,
  estimatedOutputTokens: number = 2000,
): ModelRef[] {
  return models.filter((m) => {
    // Must have API key (or be ollama)
    if (!isProviderAvailable(m.provider)) return false;

    // Must be within spend limits
    if (m.provider !== "ollama") {
      const cost = estimateCost(m, estimatedInputTokens, estimatedOutputTokens);
      if (!canSpend(cost)) return false;
    }

    // Must have enough context window
    if (estimatedInputTokens > m.contextWindow * 0.9) return false;

    return true;
  });
}

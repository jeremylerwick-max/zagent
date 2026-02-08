/**
 * Zileas Model Router — Main entry point
 * Z-32 + Z-33 + Z-34: Classify → Route → Fallback → Log
 *
 * Usage:
 *   import { routeQuery } from "./model-router/router.js";
 *   const decision = routeQuery(userMessage);
 *   // decision.actualModel → { provider: "ollama", model: "qwen2.5-coder:32b" }
 *   // decision.classification.tier → "college"
 */

import type { ModelRef, RoutingDecision, Tier } from "./types.js";
import { classifyQuery } from "./classifier.js";
import {
  resolveFallbackChain,
  estimateCost,
  recordSpend,
  canSpend,
  isProviderAvailable,
  getSpend,
} from "./api-providers.js";
import { logRoutingDecision } from "./training-logger.js";

// ── Main router ──────────────────────────────────────────────

export function routeQuery(
  query: string,
  overrideModel?: string,
  overrideTier?: Tier,
): RoutingDecision {
  const classification = classifyQuery(query);

  // Apply tier override if user forced it
  if (overrideTier) {
    const reclassified = classifyQuery(query);
    reclassified.tier = overrideTier;
    Object.assign(classification, reclassified);
  }

  const estimatedTokens = Math.ceil(query.length / 3.5);

  // If user forced a specific model, use it
  if (overrideModel) {
    const [provider, model] = overrideModel.includes("/")
      ? (overrideModel.split("/", 2) as [string, string])
      : ["ollama", overrideModel];

    const forcedModel: ModelRef = {
      provider: provider as ModelRef["provider"],
      model,
      role: "primary",
      contextWindow: 131072,
    };

    return {
      classification,
      actualModel: forcedModel,
      usedFallback: false,
      fallbackReason: undefined,
      apiCostEstimate: estimateCost(forcedModel, estimatedTokens, 2000),
      timestamp: Date.now(),
    };
  }

  // Resolve available models from fallback chain
  const allModels = [classification.selectedModel, ...classification.fallbackChain];
  const available = resolveFallbackChain(allModels, estimatedTokens);

  let actualModel: ModelRef;
  let usedFallback = false;
  let fallbackReason: string | undefined;

  if (available.length === 0) {
    // Nothing available — force qwen as last resort
    actualModel = {
      provider: "ollama",
      model: "qwen2.5-coder:32b",
      role: "primary",
      contextWindow: 32768,
    };
    usedFallback = true;
    fallbackReason = "no_models_available";
  } else if (available[0].model !== classification.selectedModel.model) {
    // Primary wasn't available, using fallback
    actualModel = available[0];
    usedFallback = true;
    fallbackReason = isProviderAvailable(classification.selectedModel.provider)
      ? "spend_limit_reached"
      : "api_key_missing";
  } else {
    actualModel = available[0];
  }

  const cost = estimateCost(actualModel, estimatedTokens, 2000);

  const decision: RoutingDecision = {
    classification,
    actualModel,
    usedFallback,
    fallbackReason,
    apiCostEstimate: cost,
    timestamp: Date.now(),
  };

  // Log for training data
  logRoutingDecision(query, classification, 0);

  return decision;
}

// ── Handle model failure (timeout, OOM, error) ───────────────

export function handleModelFailure(
  originalDecision: RoutingDecision,
  failureReason: string,
): RoutingDecision | null {
  const chain = originalDecision.classification.fallbackChain;
  const failedModel = originalDecision.actualModel.model;

  // Find next model in chain after the failed one
  const failedIdx = chain.findIndex((m) => m.model === failedModel);
  const remaining = failedIdx >= 0 ? chain.slice(failedIdx + 1) : chain;

  const estimatedTokens = 1000; // rough estimate for fallback
  const available = resolveFallbackChain(remaining, estimatedTokens);

  if (available.length === 0) return null; // nothing left to try

  const nextModel = available[0];
  const cost = estimateCost(nextModel, estimatedTokens, 2000);

  return {
    classification: originalDecision.classification,
    actualModel: nextModel,
    usedFallback: true,
    fallbackReason: `${failureReason}:${failedModel}`,
    apiCostEstimate: cost,
    timestamp: Date.now(),
  };
}

// ── Spend reporting ──────────────────────────────────────────

export function reportSpend(): string {
  const s = getSpend();
  return [
    `API Spend: $${s.daily.toFixed(4)} today / $${s.dailyLimit.toFixed(2)} limit`,
    `           $${s.monthly.toFixed(4)} this month / $${s.monthlyLimit.toFixed(2)} limit`,
  ].join("\n");
}

// ── Re-exports ───────────────────────────────────────────────

export { classifyQuery, classifyBatch } from "./classifier.js";
export { getSpend, setSpendLimits, setApiKey } from "./api-providers.js";
export { logFeedback, getEntryCount, getLogPath } from "./training-logger.js";
export { TIER_CONFIGS } from "./tiers.js";
export type { Tier, ClassificationResult, RoutingDecision, ModelRef } from "./types.js";

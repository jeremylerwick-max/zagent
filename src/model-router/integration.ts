/**
 * Zileas Router Integration Hook
 * Intercepts model selection in get-reply.ts to use query-based routing
 *
 * Usage: Called after resolveDefaultModel() to override provider/model
 * based on query classification
 */

import { routeQuery } from "./router.js";
import type { RoutingDecision } from "./types.js";

// Cache the last routing decision for the response badge
let lastDecision: RoutingDecision | null = null;

export function getLastRoutingDecision(): RoutingDecision | null {
  return lastDecision;
}

/**
 * Given a user message, classify and return the optimal model.
 * Returns null if routing is disabled or no override needed.
 */
export function resolveRoutedModel(
  userMessage: string,
  currentProvider: string,
  currentModel: string,
  overrideModel?: string,
): { provider: string; model: string; decision: RoutingDecision } | null {
  // Skip routing for empty messages
  if (!userMessage || userMessage.trim().length === 0) return null;

  // Skip routing if user explicitly forced a model via /model command
  // (overrideModel is set by the command handler)
  if (overrideModel) {
    const decision = routeQuery(userMessage, overrideModel);
    lastDecision = decision;
    return {
      provider: decision.actualModel.provider,
      model: decision.actualModel.model,
      decision,
    };
  }

  const decision = routeQuery(userMessage);
  lastDecision = decision;

  // Format for the gateway's provider/model system
  // The gateway uses "ollama" as provider name
  return {
    provider: decision.actualModel.provider,
    model: decision.actualModel.model,
    decision,
  };
}

/**
 * Format a tier badge for display in responses
 */
export function formatTierBadge(decision: RoutingDecision): string {
  const tierLabels: Record<string, string> = {
    elementary: "⚡",
    "high-school": "📝",
    college: "🔧",
    masters: "🏗️",
    phd: "🧠",
  };
  const icon = tierLabels[decision.classification.tier] ?? "❓";
  const model = `${decision.actualModel.provider}/${decision.actualModel.model}`;
  const via = decision.usedFallback ? ` (fallback: ${decision.fallbackReason})` : "";
  const cost =
    decision.apiCostEstimate && decision.apiCostEstimate > 0
      ? ` · $${decision.apiCostEstimate.toFixed(4)}`
      : "";
  return `${icon} ${decision.classification.tier}${via} · ${model}${cost}`;
}

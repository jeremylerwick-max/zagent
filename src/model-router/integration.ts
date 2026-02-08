/**
 * Zileas Model Router — Gateway Integration
 * Bridges the router into OpenClaw's model selection pipeline
 */

import { routeQuery, type RoutingDecision, type Tier } from "./router.js";

export interface RoutedModel {
  provider: string;
  model: string;
  decision: RoutingDecision;
}

/**
 * Called from get-reply.ts on every incoming message.
 * Classifies the query and returns the optimal model.
 * Returns null if routing is disabled or query is empty.
 */
export function resolveRoutedModel(
  query: string | undefined,
  currentProvider: string,
  currentModel: string,
): RoutedModel | null {
  if (!query || query.trim().length === 0) return null;

  // Skip routing for system/internal messages
  if (query.startsWith("/") || query.startsWith("!")) return null;

  try {
    const decision = routeQuery(query);
    const selected = decision.actualModel;

    // Map our provider names to OpenClaw provider format
    const providerMap: Record<string, string> = {
      ollama: "ollama",
      anthropic: "anthropic",
      openai: "openai",
      google: "google",
      openrouter: "openrouter",
    };

    return {
      provider: providerMap[selected.provider] ?? currentProvider,
      model: selected.model,
      decision,
    };
  } catch (err) {
    // If classifier fails, fall through to default model
    console.error("[model-router] Classification error:", err);
    return null;
  }
}

/**
 * Format a tier badge for logging / UI display
 */
export function formatTierBadge(decision: RoutingDecision): string {
  const tierEmoji: Record<Tier, string> = {
    elementary: "⚡",
    "high-school": "📝",
    college: "🔧",
    masters: "🏗️",
    phd: "🧠",
  };

  const emoji = tierEmoji[decision.classification.tier] ?? "❓";
  const tier = decision.classification.tier;
  const conf = (decision.classification.confidence * 100).toFixed(0);
  const model = `${decision.actualModel.provider}/${decision.actualModel.model}`;
  const ms = decision.classification.classificationTimeMs;
  const fallback = decision.usedFallback ? ` (fallback: ${decision.fallbackReason})` : "";
  const cost =
    decision.apiCostEstimate && decision.apiCostEstimate > 0
      ? ` [$${decision.apiCostEstimate.toFixed(4)}]`
      : "";

  return `${emoji} ${tier} (${conf}%) → ${model} ${ms}ms${fallback}${cost}`;
}

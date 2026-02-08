/**
 * Zileas Model Router — Type definitions
 * Z-32: Auto-router, Z-33: API fallback
 */

export type Tier = "elementary" | "high-school" | "college" | "masters" | "phd";

export interface TierConfig {
  tier: Tier;
  label: string;
  models: ModelRef[];
  maxTokens: number;
  description: string;
}

export interface ModelRef {
  provider: "ollama" | "anthropic" | "openai" | "google" | "openrouter";
  model: string;
  role: "primary" | "fallback" | "parallel";
  contextWindow: number;
  costPer1kInput?: number;
  costPer1kOutput?: number;
}

export interface ClassificationResult {
  tier: Tier;
  confidence: number; // 0-1
  signals: ClassificationSignal[];
  selectedModel: ModelRef;
  fallbackChain: ModelRef[];
  classificationTimeMs: number;
}

export interface ClassificationSignal {
  name: string;
  value: number;
  weight: number;
  contribution: number; // value * weight
}

export interface RoutingDecision {
  classification: ClassificationResult;
  actualModel: ModelRef; // may differ if primary failed
  usedFallback: boolean;
  fallbackReason?: string;
  apiCostEstimate?: number;
  timestamp: number;
}

export interface TrainingLogEntry {
  id: string;
  timestamp: number;
  query: string;
  queryTokenEstimate: number;
  classification: ClassificationResult;
  responseTimeMs: number;
  userOverride?: string; // model user picked if they overrode
  feedback?: "good" | "bad"; // thumbs up/down
}

export interface SpendTracker {
  daily: number;
  monthly: number;
  dailyLimit: number;
  monthlyLimit: number;
  lastReset: string; // ISO date
}

export interface RouterConfig {
  enabled: boolean;
  defaultTier: Tier;
  spendLimits: {
    daily: number; // USD
    monthly: number;
  };
  apiKeys: {
    anthropic?: string;
    openai?: string;
    google?: string;
    openrouter?: string;
  };
  tierOverrides?: Partial<Record<Tier, { models: ModelRef[] }>>;
}

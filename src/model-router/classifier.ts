/**
 * Zileas Query Classifier (v1 — rule-based)
 * Z-32: Classify query difficulty → select model tier
 *
 * v1: heuristic rules (word count, keywords, code detection)
 * v2: fine-tuned llama3.2:1b after ~500 training samples
 */

import type { Tier, ClassificationResult, ClassificationSignal, ModelRef } from "./types.js";
import { TIER_CONFIGS } from "./tiers.js";

// ── Signal detectors ─────────────────────────────────────────

const CODE_PATTERNS = [
  /```[\s\S]*?```/, // fenced code blocks
  /\b(function|const|let|var|class|def|import|from|return|if|for|while)\b/,
  /[{}\[\]();]=>/, // braces, arrows
  /\b(async|await|try|catch|throw)\b/,
  /\.(ts|js|py|rs|go|java|cpp|rb|sh)\b/, // file extensions
  /\b(npm|pip|cargo|docker|git|curl|wget)\b/,
];

const REASONING_KEYWORDS = [
  "why",
  "explain",
  "analyze",
  "compare",
  "evaluate",
  "critique",
  "trade-off",
  "tradeoff",
  "pros and cons",
  "should i",
  "what if",
  "implications",
  "consequences",
  "reasoning",
  "logic",
];

const ARCHITECTURE_KEYWORDS = [
  "architect",
  "design",
  "system",
  "infrastructure",
  "scale",
  "microservice",
  "database schema",
  "api design",
  "deployment",
  "migration",
  "refactor",
  "pattern",
  "framework",
];

const RESEARCH_KEYWORDS = [
  "research",
  "investigate",
  "deep dive",
  "comprehensive",
  "survey",
  "review",
  "state of the art",
  "literature",
  "compare all",
  "exhaustive",
  "thorough",
];

const SIMPLE_PATTERNS = [
  /^(hi|hello|hey|sup|yo|thanks|ok|yes|no|sure)\b/i,
  /^what (is|are|was|were) /i,
  /^(who|when|where) /i,
  /^how (much|many|old|long|far|tall) /i,
  /^\d+\s*[\+\-\*\/\^]\s*\d+/, // basic math
];

const MULTI_STEP_SIGNALS = [
  "step by step",
  "first",
  "then",
  "finally",
  "multiple",
  "workflow",
  "pipeline",
  "chain",
  "sequence",
  "process",
  "1.",
  "2.",
  "3.",
];

// ── Estimators ───────────────────────────────────────────────

function estimateTokens(text: string): number {
  return Math.ceil(text.length / 3.5); // rough char→token
}

function wordCount(text: string): number {
  return text.trim().split(/\s+/).filter(Boolean).length;
}

function hasCode(text: string): boolean {
  return CODE_PATTERNS.some((p) => p.test(text));
}

function countMatches(text: string, keywords: string[]): number {
  const lower = text.toLowerCase();
  return keywords.filter((kw) => lower.includes(kw)).length;
}

function matchesSimple(text: string): boolean {
  return SIMPLE_PATTERNS.some((p) => p.test(text.trim()));
}

// ── Signal extraction ────────────────────────────────────────

function extractSignals(query: string): ClassificationSignal[] {
  const signals: ClassificationSignal[] = [];
  const words = wordCount(query);
  const tokens = estimateTokens(query);

  // Length signal: short = easy, long = complex
  const lengthScore = Math.min(words / 50, 1); // saturate at 50 words
  signals.push({
    name: "length",
    value: lengthScore,
    weight: 0.1,
    contribution: lengthScore * 0.1,
  });

  // Simplicity: greeting/basic-question detection
  const simpleScore = matchesSimple(query) ? 1 : 0;
  signals.push({
    name: "simple_pattern",
    value: simpleScore,
    weight: 0.3,
    contribution: simpleScore * -0.3, // negative = pull toward elementary
  });

  // Code detection
  const codeScore = hasCode(query) ? 1 : 0;
  signals.push({
    name: "has_code",
    value: codeScore,
    weight: 0.25,
    contribution: codeScore * 0.25,
  });

  // Reasoning keywords
  const reasoningCount = countMatches(query, REASONING_KEYWORDS);
  const reasoningScore = Math.min(reasoningCount / 2, 1);
  signals.push({
    name: "reasoning_keywords",
    value: reasoningScore,
    weight: 0.15,
    contribution: reasoningScore * 0.15,
  });

  // Architecture/design keywords — heavy weight, these are always complex
  const archCount = countMatches(query, ARCHITECTURE_KEYWORDS);
  const archScore = Math.min(archCount / 1.5, 1); // just 2 keywords = max
  signals.push({
    name: "architecture_keywords",
    value: archScore,
    weight: 0.3,
    contribution: archScore * 0.3,
  });

  // Research keywords — also heavy, implies deep work
  const researchCount = countMatches(query, RESEARCH_KEYWORDS);
  const researchScore = Math.min(researchCount / 1.5, 1);
  signals.push({
    name: "research_keywords",
    value: researchScore,
    weight: 0.25,
    contribution: researchScore * 0.25,
  });

  // Multi-step signals
  const multiStepCount = countMatches(query, MULTI_STEP_SIGNALS);
  const multiStepScore = Math.min(multiStepCount / 2, 1);
  signals.push({
    name: "multi_step",
    value: multiStepScore,
    weight: 0.1,
    contribution: multiStepScore * 0.1,
  });

  // Token budget pressure (large input → need bigger context)
  const tokenPressure = tokens > 2000 ? 1 : tokens > 500 ? 0.5 : 0;
  signals.push({
    name: "token_pressure",
    value: tokenPressure,
    weight: 0.1,
    contribution: tokenPressure * 0.1,
  });

  return signals;
}

// ── Tier selection ───────────────────────────────────────────

function scoresToTier(totalScore: number): { tier: Tier; confidence: number } {
  // totalScore range: roughly -0.25 (very simple) to 1.0 (very complex)
  if (totalScore < 0.05) return { tier: "elementary", confidence: 0.9 - totalScore };
  if (totalScore < 0.2) return { tier: "high-school", confidence: 0.7 + totalScore };
  if (totalScore < 0.4) return { tier: "college", confidence: 0.6 + totalScore };
  if (totalScore < 0.6) return { tier: "masters", confidence: 0.5 + totalScore * 0.5 };
  return { tier: "phd", confidence: 0.4 + totalScore * 0.4 };
}

function selectModel(tier: Tier): { primary: ModelRef; fallbacks: ModelRef[] } {
  const config = TIER_CONFIGS[tier];
  if (!config || config.models.length === 0) {
    // Shouldn't happen, but safe fallback
    return {
      primary: TIER_CONFIGS["college"].models[0],
      fallbacks: TIER_CONFIGS["college"].models.slice(1),
    };
  }
  return {
    primary: config.models[0],
    fallbacks: config.models.slice(1),
  };
}

// ── Main classify function ───────────────────────────────────

export function classifyQuery(query: string): ClassificationResult {
  const start = performance.now();
  const signals = extractSignals(query);

  const totalScore = signals.reduce((sum, s) => sum + s.contribution, 0);
  const { tier, confidence } = scoresToTier(totalScore);
  const { primary, fallbacks } = selectModel(tier);

  const elapsed = performance.now() - start;

  return {
    tier,
    confidence: Math.min(Math.max(confidence, 0), 1),
    signals,
    selectedModel: primary,
    fallbackChain: fallbacks,
    classificationTimeMs: Math.round(elapsed * 100) / 100,
  };
}

// ── Test harness ─────────────────────────────────────────────

export function classifyBatch(queries: string[]): void {
  for (const q of queries) {
    const r = classifyQuery(q);
    const modelStr = `${r.selectedModel.provider}/${r.selectedModel.model}`;
    console.log(
      `[${r.tier.padEnd(12)}] (${(r.confidence * 100).toFixed(0)}%, ${r.classificationTimeMs}ms) ${modelStr.padEnd(30)} ← "${q.slice(0, 60)}"`,
    );
  }
}

#!/usr/bin/env node
/**
 * Quick test: run the classifier against sample queries
 * Usage: npx tsx src/model-router/test-classifier.ts
 */

import { classifyBatch, routeQuery, reportSpend, setApiKey } from "./router.js";

// Simulate having API keys
setApiKey("anthropic", "test-key");
setApiKey("openai", "test-key");

console.log("═══════════════════════════════════════════════════════════");
console.log("  Zileas Model Router — Classification Test");
console.log("═══════════════════════════════════════════════════════════\n");

const testQueries = [
  // Elementary
  "hi",
  "what is 5 + 5",
  "hello how are you",
  "thanks",
  "who is the president",

  // High School
  "explain how photosynthesis works",
  "summarize the main themes of 1984",
  "write a short poem about rain",
  "translate hello world to spanish",

  // College
  "write a python function to sort a linked list",
  "debug this: const x = await fetch('/api'); x.json is not a function",
  "explain the difference between TCP and UDP with code examples",
  "```python\ndef fib(n):\n  if n < 2: return n\n  return fib(n-1) + fib(n-2)\n```\noptimize this",

  // Masters
  "architect a microservice system for a CRM with 10k concurrent users",
  "design a database schema for a multi-tenant SaaS with row-level security",
  "compare all major deployment strategies for kubernetes in production",
  "review this entire codebase and suggest refactoring patterns",

  // PhD
  "research the state of the art in transformer architecture efficiency, compare all major approaches from 2023-2025, and design a novel approach combining the best elements",
  "architect a comprehensive AI orchestration platform with multi-model routing, persistent memory, tool execution, and real-time collaboration — provide detailed system design with trade-offs",
];

classifyBatch(testQueries);

console.log("\n═══════════════════════════════════════════════════════════");
console.log("  Routing Decision Details (sample)");
console.log("═══════════════════════════════════════════════════════════\n");

const decision = routeQuery("architect a CRM with voice agents and lead scoring");
console.log("Query: 'architect a CRM with voice agents and lead scoring'");
console.log(`Tier: ${decision.classification.tier}`);
console.log(`Model: ${decision.actualModel.provider}/${decision.actualModel.model}`);
console.log(`Confidence: ${(decision.classification.confidence * 100).toFixed(0)}%`);
console.log(`Time: ${decision.classification.classificationTimeMs}ms`);
console.log(`Fallback used: ${decision.usedFallback}`);
console.log(`Est. API cost: $${decision.apiCostEstimate}`);
console.log(`\nSignals:`);
for (const s of decision.classification.signals) {
  console.log(
    `  ${s.name.padEnd(22)} val=${s.value.toFixed(2)} w=${s.weight.toFixed(2)} → ${s.contribution.toFixed(3)}`,
  );
}

console.log(`\nFallback chain:`);
for (const m of decision.classification.fallbackChain) {
  console.log(`  ${m.provider}/${m.model} (${m.role})`);
}

console.log(`\n${reportSpend()}`);

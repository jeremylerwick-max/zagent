/**
 * Zileas Training Data Logger
 * Z-34: Log every routing decision for future fine-tuning
 *
 * Logs to JSONL file for later training of llama3.2:1b classifier
 */

import { appendFileSync, mkdirSync } from "node:fs";
import { join } from "node:path";
import { randomUUID } from "node:crypto";
import type { ClassificationResult, TrainingLogEntry } from "./types.js";

const LOG_DIR = join(process.env.HOME ?? "/tmp", ".openclaw", "training-data");
const LOG_FILE = join(LOG_DIR, "router-decisions.jsonl");

// Ensure directory exists
try {
  mkdirSync(LOG_DIR, { recursive: true });
} catch {
  /* ignore */
}

let entryCount = 0;

export function logRoutingDecision(
  query: string,
  classification: ClassificationResult,
  responseTimeMs: number,
  userOverride?: string,
): string {
  const entry: TrainingLogEntry = {
    id: randomUUID(),
    timestamp: Date.now(),
    query: query.slice(0, 2000), // cap for storage
    queryTokenEstimate: Math.ceil(query.length / 3.5),
    classification,
    responseTimeMs,
    userOverride,
  };

  try {
    appendFileSync(LOG_FILE, JSON.stringify(entry) + "\n");
    entryCount++;
  } catch (err) {
    // Best-effort logging, don't break the router
    console.error("[router-log] Failed to write:", err);
  }

  return entry.id;
}

export function logFeedback(entryId: string, feedback: "good" | "bad"): void {
  // Append feedback as a separate line linked by ID
  try {
    appendFileSync(
      LOG_FILE,
      JSON.stringify({
        type: "feedback",
        entryId,
        feedback,
        timestamp: Date.now(),
      }) + "\n",
    );
  } catch {
    /* ignore */
  }
}

export function getEntryCount(): number {
  return entryCount;
}

export function getLogPath(): string {
  return LOG_FILE;
}

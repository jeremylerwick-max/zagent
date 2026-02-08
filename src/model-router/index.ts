/**
 * Zileas Model Router
 * @module model-router
 */

export { routeQuery, handleModelFailure, reportSpend } from "./router.js";
export { classifyQuery, classifyBatch } from "./classifier.js";
export { setApiKey, setSpendLimits, getSpend } from "./api-providers.js";
export { logFeedback, getEntryCount, getLogPath } from "./training-logger.js";
export { TIER_CONFIGS } from "./tiers.js";
export type * from "./types.js";

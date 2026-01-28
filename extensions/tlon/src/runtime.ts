import type { PluginRuntime } from "zagent/plugin-sdk";

let runtime: PluginRuntime | null = null;

export function setTlonRuntime(next: PluginRuntime) {
  runtime = next;
}

export function getTlonRuntime(): PluginRuntime {
  if (!runtime) {
    throw new Error("Tlon runtime not initialized");
  }
  return runtime;
}

import type { ZAgentPluginApi } from "../../src/plugins/types.js";

import { createLlmTaskTool } from "./src/llm-task-tool.js";

export default function register(api: ZAgentPluginApi) {
  api.registerTool(createLlmTaskTool(api), { optional: true });
}

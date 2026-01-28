import type { ZAgentPluginApi } from "zagent/plugin-sdk";
import { emptyPluginConfigSchema } from "zagent/plugin-sdk";

import { twitchPlugin } from "./src/plugin.js";
import { setTwitchRuntime } from "./src/runtime.js";

export { monitorTwitchProvider } from "./src/monitor.js";

const plugin = {
  id: "twitch",
  name: "Twitch",
  description: "Twitch channel plugin",
  configSchema: emptyPluginConfigSchema(),
  register(api: ZAgentPluginApi) {
    setTwitchRuntime(api.runtime);
    api.registerChannel({ plugin: twitchPlugin as any });
  },
};

export default plugin;

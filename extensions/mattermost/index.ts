import type { ZAgentPluginApi } from "zagent/plugin-sdk";
import { emptyPluginConfigSchema } from "zagent/plugin-sdk";

import { mattermostPlugin } from "./src/channel.js";
import { setMattermostRuntime } from "./src/runtime.js";

const plugin = {
  id: "mattermost",
  name: "Mattermost",
  description: "Mattermost channel plugin",
  configSchema: emptyPluginConfigSchema(),
  register(api: ZAgentPluginApi) {
    setMattermostRuntime(api.runtime);
    api.registerChannel({ plugin: mattermostPlugin });
  },
};

export default plugin;

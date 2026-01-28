import type { ZAgentPluginApi } from "zagent/plugin-sdk";
import { emptyPluginConfigSchema } from "zagent/plugin-sdk";

import { nextcloudTalkPlugin } from "./src/channel.js";
import { setNextcloudTalkRuntime } from "./src/runtime.js";

const plugin = {
  id: "nextcloud-talk",
  name: "Nextcloud Talk",
  description: "Nextcloud Talk channel plugin",
  configSchema: emptyPluginConfigSchema(),
  register(api: ZAgentPluginApi) {
    setNextcloudTalkRuntime(api.runtime);
    api.registerChannel({ plugin: nextcloudTalkPlugin });
  },
};

export default plugin;

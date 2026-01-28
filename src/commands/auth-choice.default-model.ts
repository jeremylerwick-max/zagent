import type { ZAgentConfig } from "../config/config.js";
import type { WizardPrompter } from "../wizard/prompts.js";

export async function applyDefaultModelChoice(params: {
  config: ZAgentConfig;
  setDefaultModel: boolean;
  defaultModel: string;
  applyDefaultConfig: (config: ZAgentConfig) => ZAgentConfig;
  applyProviderConfig: (config: ZAgentConfig) => ZAgentConfig;
  noteDefault?: string;
  noteAgentModel: (model: string) => Promise<void>;
  prompter: WizardPrompter;
}): Promise<{ config: ZAgentConfig; agentModelOverride?: string }> {
  if (params.setDefaultModel) {
    const next = params.applyDefaultConfig(params.config);
    if (params.noteDefault) {
      await params.prompter.note(`Default model set to ${params.noteDefault}`, "Model configured");
    }
    return { config: next };
  }

  const next = params.applyProviderConfig(params.config);
  await params.noteAgentModel(params.defaultModel);
  return { config: next, agentModelOverride: params.defaultModel };
}

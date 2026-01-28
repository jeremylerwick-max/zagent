import path from "node:path";
import { describe, expect, it } from "vitest";
import { formatCliCommand } from "./command-format.js";
import { applyCliProfileEnv, parseCliProfileArgs } from "./profile.js";

describe("parseCliProfileArgs", () => {
  it("leaves gateway --dev for subcommands", () => {
    const res = parseCliProfileArgs([
      "node",
      "zagent",
      "gateway",
      "--dev",
      "--allow-unconfigured",
    ]);
    if (!res.ok) throw new Error(res.error);
    expect(res.profile).toBeNull();
    expect(res.argv).toEqual(["node", "zagent", "gateway", "--dev", "--allow-unconfigured"]);
  });

  it("still accepts global --dev before subcommand", () => {
    const res = parseCliProfileArgs(["node", "zagent", "--dev", "gateway"]);
    if (!res.ok) throw new Error(res.error);
    expect(res.profile).toBe("dev");
    expect(res.argv).toEqual(["node", "zagent", "gateway"]);
  });

  it("parses --profile value and strips it", () => {
    const res = parseCliProfileArgs(["node", "zagent", "--profile", "work", "status"]);
    if (!res.ok) throw new Error(res.error);
    expect(res.profile).toBe("work");
    expect(res.argv).toEqual(["node", "zagent", "status"]);
  });

  it("rejects missing profile value", () => {
    const res = parseCliProfileArgs(["node", "zagent", "--profile"]);
    expect(res.ok).toBe(false);
  });

  it("rejects combining --dev with --profile (dev first)", () => {
    const res = parseCliProfileArgs(["node", "zagent", "--dev", "--profile", "work", "status"]);
    expect(res.ok).toBe(false);
  });

  it("rejects combining --dev with --profile (profile first)", () => {
    const res = parseCliProfileArgs(["node", "zagent", "--profile", "work", "--dev", "status"]);
    expect(res.ok).toBe(false);
  });
});

describe("applyCliProfileEnv", () => {
  it("fills env defaults for dev profile", () => {
    const env: Record<string, string | undefined> = {};
    applyCliProfileEnv({
      profile: "dev",
      env,
      homedir: () => "/home/peter",
    });
    const expectedStateDir = path.join("/home/peter", ".zagent-dev");
    expect(env.ZAGENT_PROFILE).toBe("dev");
    expect(env.ZAGENT_STATE_DIR).toBe(expectedStateDir);
    expect(env.ZAGENT_CONFIG_PATH).toBe(path.join(expectedStateDir, "zagent.json"));
    expect(env.ZAGENT_GATEWAY_PORT).toBe("19001");
  });

  it("does not override explicit env values", () => {
    const env: Record<string, string | undefined> = {
      ZAGENT_STATE_DIR: "/custom",
      ZAGENT_GATEWAY_PORT: "19099",
    };
    applyCliProfileEnv({
      profile: "dev",
      env,
      homedir: () => "/home/peter",
    });
    expect(env.ZAGENT_STATE_DIR).toBe("/custom");
    expect(env.ZAGENT_GATEWAY_PORT).toBe("19099");
    expect(env.ZAGENT_CONFIG_PATH).toBe(path.join("/custom", "zagent.json"));
  });
});

describe("formatCliCommand", () => {
  it("returns command unchanged when no profile is set", () => {
    expect(formatCliCommand("zagent doctor --fix", {})).toBe("zagent doctor --fix");
  });

  it("returns command unchanged when profile is default", () => {
    expect(formatCliCommand("zagent doctor --fix", { ZAGENT_PROFILE: "default" })).toBe(
      "zagent doctor --fix",
    );
  });

  it("returns command unchanged when profile is Default (case-insensitive)", () => {
    expect(formatCliCommand("zagent doctor --fix", { ZAGENT_PROFILE: "Default" })).toBe(
      "zagent doctor --fix",
    );
  });

  it("returns command unchanged when profile is invalid", () => {
    expect(formatCliCommand("zagent doctor --fix", { ZAGENT_PROFILE: "bad profile" })).toBe(
      "zagent doctor --fix",
    );
  });

  it("returns command unchanged when --profile is already present", () => {
    expect(
      formatCliCommand("zagent --profile work doctor --fix", { ZAGENT_PROFILE: "work" }),
    ).toBe("zagent --profile work doctor --fix");
  });

  it("returns command unchanged when --dev is already present", () => {
    expect(formatCliCommand("zagent --dev doctor", { ZAGENT_PROFILE: "dev" })).toBe(
      "zagent --dev doctor",
    );
  });

  it("inserts --profile flag when profile is set", () => {
    expect(formatCliCommand("zagent doctor --fix", { ZAGENT_PROFILE: "work" })).toBe(
      "zagent --profile work doctor --fix",
    );
  });

  it("trims whitespace from profile", () => {
    expect(formatCliCommand("zagent doctor --fix", { ZAGENT_PROFILE: "  jbclawd  " })).toBe(
      "zagent --profile jbclawd doctor --fix",
    );
  });

  it("handles command with no args after zagent", () => {
    expect(formatCliCommand("zagent", { ZAGENT_PROFILE: "test" })).toBe(
      "zagent --profile test",
    );
  });

  it("handles pnpm wrapper", () => {
    expect(formatCliCommand("pnpm zagent doctor", { ZAGENT_PROFILE: "work" })).toBe(
      "pnpm zagent --profile work doctor",
    );
  });
});

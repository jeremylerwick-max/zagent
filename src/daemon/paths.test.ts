import path from "node:path";

import { describe, expect, it } from "vitest";

import { resolveGatewayStateDir } from "./paths.js";

describe("resolveGatewayStateDir", () => {
  it("uses the default state dir when no overrides are set", () => {
    const env = { HOME: "/Users/test" };
    expect(resolveGatewayStateDir(env)).toBe(path.join("/Users/test", ".zagent"));
  });

  it("appends the profile suffix when set", () => {
    const env = { HOME: "/Users/test", ZAGENT_PROFILE: "rescue" };
    expect(resolveGatewayStateDir(env)).toBe(path.join("/Users/test", ".zagent-rescue"));
  });

  it("treats default profiles as the base state dir", () => {
    const env = { HOME: "/Users/test", ZAGENT_PROFILE: "Default" };
    expect(resolveGatewayStateDir(env)).toBe(path.join("/Users/test", ".zagent"));
  });

  it("uses ZAGENT_STATE_DIR when provided", () => {
    const env = { HOME: "/Users/test", ZAGENT_STATE_DIR: "/var/lib/zagent" };
    expect(resolveGatewayStateDir(env)).toBe(path.resolve("/var/lib/zagent"));
  });

  it("expands ~ in ZAGENT_STATE_DIR", () => {
    const env = { HOME: "/Users/test", ZAGENT_STATE_DIR: "~/zagent-state" };
    expect(resolveGatewayStateDir(env)).toBe(path.resolve("/Users/test/zagent-state"));
  });

  it("preserves Windows absolute paths without HOME", () => {
    const env = { ZAGENT_STATE_DIR: "C:\\State\\zagent" };
    expect(resolveGatewayStateDir(env)).toBe("C:\\State\\zagent");
  });
});

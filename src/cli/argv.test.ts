import { describe, expect, it } from "vitest";

import {
  buildParseArgv,
  getFlagValue,
  getCommandPath,
  getPrimaryCommand,
  getPositiveIntFlagValue,
  getVerboseFlag,
  hasHelpOrVersion,
  hasFlag,
  shouldMigrateState,
  shouldMigrateStateFromPath,
} from "./argv.js";

describe("argv helpers", () => {
  it("detects help/version flags", () => {
    expect(hasHelpOrVersion(["node", "zagent", "--help"])).toBe(true);
    expect(hasHelpOrVersion(["node", "zagent", "-V"])).toBe(true);
    expect(hasHelpOrVersion(["node", "zagent", "status"])).toBe(false);
  });

  it("extracts command path ignoring flags and terminator", () => {
    expect(getCommandPath(["node", "zagent", "status", "--json"], 2)).toEqual(["status"]);
    expect(getCommandPath(["node", "zagent", "agents", "list"], 2)).toEqual(["agents", "list"]);
    expect(getCommandPath(["node", "zagent", "status", "--", "ignored"], 2)).toEqual(["status"]);
  });

  it("returns primary command", () => {
    expect(getPrimaryCommand(["node", "zagent", "agents", "list"])).toBe("agents");
    expect(getPrimaryCommand(["node", "zagent"])).toBeNull();
  });

  it("parses boolean flags and ignores terminator", () => {
    expect(hasFlag(["node", "zagent", "status", "--json"], "--json")).toBe(true);
    expect(hasFlag(["node", "zagent", "--", "--json"], "--json")).toBe(false);
  });

  it("extracts flag values with equals and missing values", () => {
    expect(getFlagValue(["node", "zagent", "status", "--timeout", "5000"], "--timeout")).toBe(
      "5000",
    );
    expect(getFlagValue(["node", "zagent", "status", "--timeout=2500"], "--timeout")).toBe("2500");
    expect(getFlagValue(["node", "zagent", "status", "--timeout"], "--timeout")).toBeNull();
    expect(getFlagValue(["node", "zagent", "status", "--timeout", "--json"], "--timeout")).toBe(
      null,
    );
    expect(getFlagValue(["node", "zagent", "--", "--timeout=99"], "--timeout")).toBeUndefined();
  });

  it("parses verbose flags", () => {
    expect(getVerboseFlag(["node", "zagent", "status", "--verbose"])).toBe(true);
    expect(getVerboseFlag(["node", "zagent", "status", "--debug"])).toBe(false);
    expect(getVerboseFlag(["node", "zagent", "status", "--debug"], { includeDebug: true })).toBe(
      true,
    );
  });

  it("parses positive integer flag values", () => {
    expect(getPositiveIntFlagValue(["node", "zagent", "status"], "--timeout")).toBeUndefined();
    expect(
      getPositiveIntFlagValue(["node", "zagent", "status", "--timeout"], "--timeout"),
    ).toBeNull();
    expect(
      getPositiveIntFlagValue(["node", "zagent", "status", "--timeout", "5000"], "--timeout"),
    ).toBe(5000);
    expect(
      getPositiveIntFlagValue(["node", "zagent", "status", "--timeout", "nope"], "--timeout"),
    ).toBeUndefined();
  });

  it("builds parse argv from raw args", () => {
    const nodeArgv = buildParseArgv({
      programName: "zagent",
      rawArgs: ["node", "zagent", "status"],
    });
    expect(nodeArgv).toEqual(["node", "zagent", "status"]);

    const versionedNodeArgv = buildParseArgv({
      programName: "zagent",
      rawArgs: ["node-22", "zagent", "status"],
    });
    expect(versionedNodeArgv).toEqual(["node-22", "zagent", "status"]);

    const versionedNodeWindowsArgv = buildParseArgv({
      programName: "zagent",
      rawArgs: ["node-22.2.0.exe", "zagent", "status"],
    });
    expect(versionedNodeWindowsArgv).toEqual(["node-22.2.0.exe", "zagent", "status"]);

    const versionedNodePatchlessArgv = buildParseArgv({
      programName: "zagent",
      rawArgs: ["node-22.2", "zagent", "status"],
    });
    expect(versionedNodePatchlessArgv).toEqual(["node-22.2", "zagent", "status"]);

    const versionedNodeWindowsPatchlessArgv = buildParseArgv({
      programName: "zagent",
      rawArgs: ["node-22.2.exe", "zagent", "status"],
    });
    expect(versionedNodeWindowsPatchlessArgv).toEqual(["node-22.2.exe", "zagent", "status"]);

    const versionedNodeWithPathArgv = buildParseArgv({
      programName: "zagent",
      rawArgs: ["/usr/bin/node-22.2.0", "zagent", "status"],
    });
    expect(versionedNodeWithPathArgv).toEqual(["/usr/bin/node-22.2.0", "zagent", "status"]);

    const nodejsArgv = buildParseArgv({
      programName: "zagent",
      rawArgs: ["nodejs", "zagent", "status"],
    });
    expect(nodejsArgv).toEqual(["nodejs", "zagent", "status"]);

    const nonVersionedNodeArgv = buildParseArgv({
      programName: "zagent",
      rawArgs: ["node-dev", "zagent", "status"],
    });
    expect(nonVersionedNodeArgv).toEqual(["node", "zagent", "node-dev", "zagent", "status"]);

    const directArgv = buildParseArgv({
      programName: "zagent",
      rawArgs: ["zagent", "status"],
    });
    expect(directArgv).toEqual(["node", "zagent", "status"]);

    const bunArgv = buildParseArgv({
      programName: "zagent",
      rawArgs: ["bun", "src/entry.ts", "status"],
    });
    expect(bunArgv).toEqual(["bun", "src/entry.ts", "status"]);
  });

  it("builds parse argv from fallback args", () => {
    const fallbackArgv = buildParseArgv({
      programName: "zagent",
      fallbackArgv: ["status"],
    });
    expect(fallbackArgv).toEqual(["node", "zagent", "status"]);
  });

  it("decides when to migrate state", () => {
    expect(shouldMigrateState(["node", "zagent", "status"])).toBe(false);
    expect(shouldMigrateState(["node", "zagent", "health"])).toBe(false);
    expect(shouldMigrateState(["node", "zagent", "sessions"])).toBe(false);
    expect(shouldMigrateState(["node", "zagent", "memory", "status"])).toBe(false);
    expect(shouldMigrateState(["node", "zagent", "agent", "--message", "hi"])).toBe(false);
    expect(shouldMigrateState(["node", "zagent", "agents", "list"])).toBe(true);
    expect(shouldMigrateState(["node", "zagent", "message", "send"])).toBe(true);
  });

  it("reuses command path for migrate state decisions", () => {
    expect(shouldMigrateStateFromPath(["status"])).toBe(false);
    expect(shouldMigrateStateFromPath(["agents", "list"])).toBe(true);
  });
});

import { describe, it, expect, vi } from "vitest";
import * as merger from "../src/config/merger";
import * as fs from "fs";

vi.mock("fs");

describe("merger", () => {
  it("extracts flat env", () => {
    const config = {
      API_KEY: "123",
      other: "value"
    };
    const merged = merger.mergeConfigs(config, {});
    expect(merged).toEqual({ API_KEY: "123" });
  });

  it("extracts from env object", () => {
    const config = {
      env: {
        TOKEN: "abc",
        NUM: 1
      }
    };
    const merged = merger.mergeConfigs({}, config);
    expect(merged).toEqual({ TOKEN: "abc", NUM: "1" });
  });

  it("extracts from mcpServers gaia env", () => {
    const config = {
      mcpServers: {
        gaia: {
          env: {
            GAIA_TOKEN: "xyz"
          }
        }
      }
    };
    const merged = merger.mergeConfigs(config, {});
    expect(merged).toEqual({ GAIA_TOKEN: "xyz" });
  });

  it("merges global and local correctly, local overrides", () => {
    const globalConfig = { API_KEY: "global123", GLOBAL_ONLY: "yes" };
    const localConfig = { API_KEY: "local123", LOCAL_ONLY: "yes" };
    
    const merged = merger.mergeConfigs(globalConfig, localConfig);
    expect(merged).toEqual({
      API_KEY: "local123",
      GLOBAL_ONLY: "yes",
      LOCAL_ONLY: "yes"
    });
  });
});

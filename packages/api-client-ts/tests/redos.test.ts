import { describe, it, expect } from "vitest";
import { GaiaClient } from "../src/client.js";

describe("GaiaClient ReDoS", () => {
  it("handles excessive trailing slashes without ReDoS", () => {
    const client1 = new GaiaClient({ baseUrl: "https://x.test" + "/".repeat(50000) });
    expect((client1 as any).baseUrl).toBe("https://x.test");

    const client2 = new GaiaClient({ baseUrl: "https://x.test" });
    expect((client2 as any).baseUrl).toBe("https://x.test");
  });
});

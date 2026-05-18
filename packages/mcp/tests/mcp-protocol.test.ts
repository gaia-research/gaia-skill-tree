import { describe, it, expect, beforeAll, afterAll } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { createServer } from "../src/index.js";
import mcpPackage from "../package.json";

describe("MCP protocol layer", () => {
  let client: Client;

  beforeAll(async () => {
    const server = createServer();
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
    await server.connect(serverTransport);
    client = new Client({ name: "test-client", version: "1.0.0" });
    await client.connect(clientTransport);
  });

  afterAll(async () => {
    await client.close();
  });

  // ── Server identity ──────────────────────────────────────────────────────

  it("reports server name and package version after initialize", () => {
    const info = client.getServerVersion();
    expect(info?.name).toBe("gaia-skill-registry");
    expect(info?.version).toBe(mcpPackage.version);
  });

  // ── tools/list ───────────────────────────────────────────────────────────

  it("exposes exactly the 5 expected tools", async () => {
    const { tools } = await client.listTools();
    const names = tools.map((t) => t.name).sort();
    expect(names).toEqual([
      "gaia_lookup",
      "gaia_my_tree",
      "gaia_propose",
      "gaia_scan_context",
      "gaia_suggest",
    ]);
  });

  it("all tools have inputSchema and description", async () => {
    const { tools } = await client.listTools();
    for (const tool of tools) {
      expect(tool.description, `${tool.name} missing description`).toBeTruthy();
      expect(tool.inputSchema, `${tool.name} missing inputSchema`).toBeTruthy();
    }
  });

  // ── gaia_lookup ──────────────────────────────────────────────────────────

  it("gaia_lookup returns skill metadata for a known ID", async () => {
    const result = await client.callTool({ name: "gaia_lookup", arguments: { query: "web-search" } });
    const text = getText(result);
    expect(text).toContain("web-search");
    expect(text).toContain("Web Search");
  });

  it("gaia_lookup handles an unknown skill ID without throwing", async () => {
    const result = await client.callTool({
      name: "gaia_lookup",
      arguments: { query: "this-skill-does-not-exist-xyz" },
    });
    expect(getText(result).length).toBeGreaterThan(0);
  });

  // ── gaia_my_tree ─────────────────────────────────────────────────────────

  it("gaia_my_tree returns a message when no user is configured", async () => {
    const saved = process.env.GAIA_USER;
    delete process.env.GAIA_USER;
    try {
      const result = await client.callTool({ name: "gaia_my_tree", arguments: {} });
      expect(getText(result).length).toBeGreaterThan(0);
    } finally {
      if (saved !== undefined) process.env.GAIA_USER = saved;
    }
  });

  it("gaia_my_tree accepts an explicit username", async () => {
    const result = await client.callTool({
      name: "gaia_my_tree",
      arguments: { username: "mbtiongson1" },
    });
    const text = getText(result);
    expect(text.length).toBeGreaterThan(0);
  });

  // ── gaia_propose ─────────────────────────────────────────────────────────

  it("gaia_propose returns a descriptive error when GITHUB_TOKEN is absent", async () => {
    const savedToken = process.env.GITHUB_TOKEN;
    const savedGh = process.env.GH_TOKEN;
    const savedUser = process.env.GAIA_USER;
    delete process.env.GITHUB_TOKEN;
    delete process.env.GH_TOKEN;
    process.env.GAIA_USER = "test-user";
    try {
      const result = await client.callTool({
        name: "gaia_propose",
        arguments: { skillId: "web-search", type: "basic" },
      });
      expect(getText(result).toLowerCase()).toMatch(/token/);
    } finally {
      if (savedToken !== undefined) process.env.GITHUB_TOKEN = savedToken;
      if (savedGh !== undefined) process.env.GH_TOKEN = savedGh;
      if (savedUser !== undefined) process.env.GAIA_USER = savedUser;
      else delete process.env.GAIA_USER;
    }
  });

  // ── gaia_suggest / gaia_scan_context ─────────────────────────────────────

  it("gaia_suggest returns text content", async () => {
    const result = await client.callTool({
      name: "gaia_suggest",
      arguments: { context: ["building a web scraper"], tools: ["bash"] },
    });
    expect(getText(result).length).toBeGreaterThan(0);
  });

  it("gaia_scan_context returns text content", async () => {
    const result = await client.callTool({
      name: "gaia_scan_context",
      arguments: { connectedTools: ["bash", "read_file"], projectSignals: ["vitest in package.json"] },
    });
    expect(getText(result).length).toBeGreaterThan(0);
  });

  // ── resources ────────────────────────────────────────────────────────────

  it("exposes the gaia://registry static resource", async () => {
    const { resources } = await client.listResources();
    const uris = resources.map((r) => r.uri);
    expect(uris).toContain("gaia://registry");
  });

  it("exposes a gaia://tree/{username} resource template", async () => {
    const { resourceTemplates } = await client.listResourceTemplates();
    const templates = resourceTemplates.map((r) => r.uriTemplate);
    expect(templates.some((t) => t.includes("tree"))).toBe(true);
  });

  it("gaia://registry returns valid JSON with a skills key", async () => {
    const result = await client.readResource({ uri: "gaia://registry" });
    const text = (result.contents[0] as { text: string }).text;
    const data = JSON.parse(text);
    expect(data).toHaveProperty("skills");
  });
});

function getText(result: Awaited<ReturnType<Client["callTool"]>>): string {
  return (result.content[0] as { type: string; text: string }).text;
}

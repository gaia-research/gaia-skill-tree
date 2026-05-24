import { McpServer, ResourceTemplate } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createRequire } from "module";
import { z } from "zod";
import { lookupSkill } from "./tools/lookup.js";
import { getMyTree } from "./tools/myTree.js";
import { suggest } from "./tools/suggest.js";
import { scanContext } from "./tools/scanContext.js";
import { propose } from "./tools/propose.js";
import { getRegistryResource, getUserTreeResource } from "./resources/registry.js";
import { withErrorHandling } from "./utils/errors.js";

const require = createRequire(import.meta.url);

function readPackageVersion(): string {
  for (const packagePath of ["../package.json", "../../package.json"]) {
    try {
      return (require(packagePath) as { version: string }).version;
    } catch {
      // Try the next relative path. Source runs from src/, compiled code runs from dist/src/.
    }
  }
  throw new Error("Unable to read package version for MCP server");
}

const version = readPackageVersion();

export function createServer(): McpServer {
  const server = new McpServer({
    name: "gaia-skill-registry",
    version,
  });

  server.tool(
    "gaia_lookup",
    "Look up a skill in the Gaia registry by ID or fuzzy name. Returns full metadata, prerequisites, derivatives, evidence, and graph context.",
    { query: z.string().describe("Skill ID (e.g. 'web-scrape') or fuzzy name (e.g. 'web scraping')") },
    withErrorHandling(async ({ query }) => {
      return await lookupSkill(query);
    })
  );

  server.tool(
    "gaia_my_tree",
    "Show the current user's Gaia skill tree — unlocked skills, pending fusions, and progression stats.",
    { username: z.string().regex(/^[a-zA-Z0-9][a-zA-Z0-9-]*$/, "Invalid GitHub username").max(39).optional().describe("GitHub username (defaults to configured GAIA_USER)") },
    withErrorHandling(async ({ username }) => {
      return await getMyTree(username);
    })
  );

  server.tool(
    "gaia_suggest",
    "Get skill fusion suggestions based on current context. Detects what you're building and recommends achievable fusions or skills you're one step away from unlocking.",
    {
      context: z.array(z.string()).optional().describe("Project signals — descriptions of what you're building, package names, file patterns"),
      tools: z.array(z.string()).optional().describe("Names of MCP tools currently connected (e.g. 'web_search', 'bash', 'fetch')"),
    },
    withErrorHandling(async ({ context, tools }) => {
      return await suggest(context, tools);
    })
  );

  server.tool(
    "gaia_scan_context",
    "Scan your current project context to detect skills in use. Pass connected MCP tool names and project signals to identify skills and discover fusion opportunities.",
    {
      connectedTools: z.array(z.string()).optional().describe("MCP tool names currently available (e.g. 'web_search', 'read_file', 'bash')"),
      projectSignals: z.array(z.string()).optional().describe("Descriptions of project capabilities (e.g. 'cheerio in package.json', 'building a web scraper')"),
      deepScan: z.boolean().optional().describe("If true, invokes the local 'gaia' CLI to perform a deep source code scan for skill tokens."),
    },
    withErrorHandling(async ({ connectedTools, projectSignals, deepScan }) => {
      return await scanContext(connectedTools, projectSignals, deepScan);
    })
  );

  server.tool(
    "gaia_propose",
    "Claim a skill fusion or propose a novel skill to the Gaia registry. Opens a PR on GitHub. Requires GITHUB_TOKEN env var.",
    {
      skillId: z.string().optional().describe("ID of an existing skill to fuse/claim (e.g. 'web-scrape')"),
      name: z.string().optional().describe("Name for a novel skill proposal"),
      description: z.string().optional().describe("Description of the novel skill"),
      type: z.enum(["basic", "extra", "unique", "ultimate"]).optional().describe("Skill type"),
      prerequisites: z.array(z.string()).optional().describe("Prerequisite skill IDs for extra/ultimate proposals"),
    },
    withErrorHandling(async (input) => {
      return await propose(input);
    })
  );

  server.resource(
    "gaia-registry",
    "gaia://registry",
    async () => {
      const data = await getRegistryResource();
      return { contents: [{ uri: "gaia://registry", text: data, mimeType: "application/json" }] };
    }
  );

  server.resource(
    "gaia-tree",
    new ResourceTemplate("gaia://tree/{username}", { list: undefined }),
    async (uri) => {
      const username = uri.pathname.split("/").pop() ?? "";
      const data = await getUserTreeResource(username);
      return { contents: [{ uri: uri.href, text: data, mimeType: "application/json" }] };
    }
  );

  return server;
}

export async function startServer(): Promise<void> {
  const server = createServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

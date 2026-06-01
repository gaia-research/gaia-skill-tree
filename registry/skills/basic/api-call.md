# [huggingface](../../../docs/u/huggingface/)/hf-cli  [2★]
**ID:** api-call  
**Type:** Basic Skill  
**Rank:** _rank-less generic reference — stars are earned by named implementations_  
**Top named variant:** 2★  
**Skill Call:** `/api-call`

---

**Summary:** A fundamental skill that enables agents to interact with external services via HTTP API calls.

## Description
Constructs, executes, and handles responses from HTTP APIs by interpreting documentation and selecting appropriate endpoints and parameters. This skill allows agents to fetch dynamic data, trigger remote actions, and interact with external systems programmatically by adhering to OpenAPI or other API specifications.

## Use Case
Useful for tasks that require real-time data fetching, invoking external web services, integrating with SaaS platforms (e.g., GitHub, Slack, JIRA), or triggering automated workflows via standard REST or GraphQL endpoints.

## Directives
- Identify the correct HTTP method (GET, POST, PUT, DELETE) and endpoint for the task.
- Parse the API documentation to construct the required headers, authentication tokens, and request body.
- Handle API responses gracefully, checking HTTP status codes and parsing JSON or XML payloads.
- Implement retry logic or error handling for rate limits, timeouts, and unexpected responses.

## Prerequisites
_None._

## Unlocks
- [Function Calling](../extra/function-calling.md)
- [Workflow Automation](../extra/workflow-automation.md)
- [MCP Server Creation](../extra/mcp-server-creation.md)

## Named Implementations
| Named Skill | Contributor | Stars | Evidence |
|---|---|---|---|
| huggingface/hf-cli | huggingface | 2★ | 0 |

## Evidence (inherited capability)
_Capability-level evidence for this generic reference. Every named implementation above inherits it._

| Class | Source | Evaluator | Date |
|---|---|---|---|
| A | https://arxiv.org/abs/2305.15334 | mbtiongson1 | 2026-04-28 |

## Known Agents
_None verified yet._

---

---
type: "AI Agent Skill"
title: "API Call"
description: "A fundamental skill that enables agents to interact with external services via HTTP API calls."
resource: "https://gaia.tiongson.co/codex.html#api-call"
tags: ["gaia-skill-tree", "basic-skill"]
timestamp: "2026-06-21T00:00:00Z"
---

# API Call

## Description

Constructs, executes, and handles responses from HTTP APIs by interpreting documentation and selecting appropriate endpoints and parameters. This skill allows agents to fetch dynamic data, trigger remote actions, and interact with external systems programmatically by adhering to OpenAPI or other API specifications.

## Use Case

Useful for tasks that require real-time data fetching, invoking external web services, integrating with SaaS platforms (e.g., GitHub, Slack, JIRA), or triggering automated workflows via standard REST or GraphQL endpoints.

## Directives

- Identify the correct HTTP method (GET, POST, PUT, DELETE) and endpoint for the task.
- Parse the API documentation to construct the required headers, authentication tokens, and request body.
- Handle API responses gracefully, checking HTTP status codes and parsing JSON or XML payloads.
- Implement retry logic or error handling for rate limits, timeouts, and unexpected responses.

## Derivatives

- [Function Calling](/skills/extra/function-calling.md)
- [Workflow Automation](/skills/extra/workflow-automation.md)
- [MCP Server Creation](/skills/extra/mcp-server-creation.md)


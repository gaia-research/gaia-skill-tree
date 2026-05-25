---
id: intelligentcode-ai/mcp-client
name: MCP Client
contributor: intelligentcode-ai
origin: false
links:
  github: https://github.com/intelligentcode-ai/skills/blob/main/skills/mcp-client/SKILL.md
genericSkillRef: mcp-integration
status: named
title: The Protocol Bridge
catalogRef: intelligentcode-ai-mcp-client
level: 2★
description: Portable CLI tool that connects to MCP servers on-demand, enumerates
  available tools, displays them, and executes calls — works with any MCP-compatible
  backend without platform lock-in.
tags:
- mcp
- model-context-protocol
- tool-integration
- cli
updatedAt: '2026-05-25'
---

## Overview

A universal MCP client that treats server connections as ephemeral: connect, list tools, call, disconnect. Designed for use inside agent loops where the set of available MCP servers may change between turns.

## Key behaviours

- Enumerates all tools exposed by a target MCP server at connection time
- Executes tool calls with structured arguments and returns typed responses
- Handles multi-server routing — each call specifies the server by name or URL
- Authentication is handled via environment variables; no credentials in prompts

## Source

[intelligentcode-ai/skills — mcp-client/SKILL.md](https://github.com/intelligentcode-ai/skills/blob/main/skills/mcp-client/SKILL.md)

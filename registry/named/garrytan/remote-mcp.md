---
id: garrytan/remote-mcp
name: remote-mcp
contributor: garrytan
origin: false
genericSkillRef: mcp-server-deployment
status: named
level: 2★
description: 'Publish the user''s own gbrain over MCP so other devices, desktop apps
  and

  cloud agents can reach it. `gbrain mcp expose` installs and signs in

  Tailscale, publishes the running `gbrain serve --http` on the tailnet

  (HTTPS, tailnet-only by default; Funnel only when a client lives in a

  vendor cloud), keeps the server alive as a user service, and hands back the

  MCP URL. Then grant one least-privilege client per consumer, install the

  handoff inside that client, and verify a real memory round trip.'
createdAt: '2026-09-23'
updatedAt: '2026-09-23'
title: remote-mcp
links:
  github: https://github.com/garrytan/gbrain/blob/v0.51.6.0/plugin/skills/remote-mcp/SKILL.md
timeline:
- timestamp: '2026-09-23T06:08:12Z'
  action: add
  contributor: unknown
  details: Added named skill garrytan/remote-mcp
---

## Installation
Add installation instructions here.

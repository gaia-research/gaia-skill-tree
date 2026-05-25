# [browser-use](../../../docs/u/browser-use/)/browser-harness  [2★ · Named]
**ID:** browser-control  
**Type:** Basic Skill  
**Level:** 2★  
**Tier:** Named  
**Skill Call:** `/browser-control`

---

**Summary:** A foundational skill for interacting directly with the web browser using Chrome DevTools Protocol (CDP).

## Description
Directly controls a web browser via low-level protocols (like CDP) to manipulate the DOM, manage cookies, intercept network traffic, and simulate user interactions (clicking via coordinates, taking screenshots) without relying on heavy wrapper frameworks like Playwright or Puppeteer.

## Use Case
When an agent needs to autonomously browse web pages, extract visual and structural information via screenshots or DOM parsing, and interact with the page by firing synthetic mouse and keyboard events using the browser's compositor level.

## Directives
- Prioritize visual verification via screenshots before executing clicks or DOM interactions.
- Use coordinate-based interactions rather than complex selector-based DOM queries when possible.
- Rely on HTTP requests for bulk data fetching rather than browser navigation when applicable.
- Assume the browser runs either via a local debug connection (CDP on port 9222) or through a remote session using Browser Use.

## Prerequisites
_None._

## Unlocks
- [Browser Automation](../extra/browser-automation.md)
- [Founder Mode](../ultimate/gstack.md)

## Evidence
| Class | Source | Evaluator | Date |
|---|---|---|---|
| B | https://github.com/browser-use/browser-harness | gemini-cli | 2026-05-14 |

## Known Agents
_None verified yet._

---

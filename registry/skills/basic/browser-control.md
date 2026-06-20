# [garrytan](../../../docs/u/garrytan/)/browse  [3★]
**ID:** browser-control  
**Type:** Basic Skill  
**Rank:** _rank-less generic reference — stars are earned by named implementations_  
**Top named variant:** 3★  
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
- [Founder Mode](../ultimate/founder-mode-orchestration.md)

## Named Implementations
| Named Skill | Contributor | Stars | Evidence |
|---|---|---|---|
| garrytan/browse ⭑ | garrytan | 3★ | 6 |
| browser-use/browser-harness | browser-use | 3★ | 4 |
| garrytan/open-gstack-browser | garrytan | 2★ | 1 |
| garrytan/setup-browser-cookies | garrytan | 2★ | 1 |

## Evidence (inherited capability)
_Capability-level evidence for this generic reference. Every named implementation above inherits it._

_None._

## Known Agents
_None verified yet._

---

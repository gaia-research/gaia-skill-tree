---
name: terminal-simulation
description: >-
  Generate interactive, animated, responsive HTML-based terminal simulators to
  showcase CLI commands, scripts, pipelines, or interactive workflows. Use this
  whenever you need to visually showcase a command line sequence, mock interactive
  CLI tools, or simulate code executions.
version: 1.0.0
---

# terminal-simulation

An agent skill for implementing highly polished, interactive terminal/CLI simulators in web applications or documentations. Rather than presenting static command blocks, this skill details how to render a responsive console that animates log sequences, provides interactive review inputs, and handles error gates.

```
┌──────────────────────────────────────────────┐
│ curate-chain-simulator.sh             [Run]  │
├──────────────────────────────────────────────┤
│ > Initiating Explore-class Sub-Agent...      │
│ [L1] Reading registry/gaia.json...           │
│ [Gate g1] PASS! 142 existingIds loaded       │
│                                              │
│ [L4] Review Intake Batch:                    │
│ ┌──────────────────────────────────────────┐ │
│ │ Candidate       │ Type    │ Decision     │ │
│ ├─────────────────┼─────────┼──────────────┤ │
│ │ lit-search      │ generic │ [Accept  v]  │ │
│ └─────────────────┴─────────┴──────────────┘ │
│ [Submit Decisions]                           │
└──────────────────────────────────────────────┘
```

---

## Template Components

Use the following markup, styles, and script structure to generate a terminal simulator.

### 1. HTML Structure

```html
<div class="simulator-wrapper" id="simWrapper">
  <div class="simulator-header">
    <div class="simulator-dots">
      <span class="dot red"></span>
      <span class="dot yellow"></span>
      <span class="dot green"></span>
    </div>
    <div class="simulator-title">cli-simulator.sh</div>
    <button class="simulator-btn" id="startSimBtn">Run Simulation</button>
  </div>
  <div class="simulator-body" id="simulatorConsole">
    <div class="console-line system">> Click "Run Simulation" to start the command demonstration.</div>
  </div>
</div>
```

### 2. Premium CSS (Dark Theme, Responsive)

Inject this block into the head or append it to the main stylesheet. It uses CSS custom variables to inherit existing themes:

```css
.simulator-wrapper {
  background: #08080a;
  border: 1px solid var(--border, #222);
  border-radius: 12px;
  overflow: hidden;
  margin: 2rem 0;
  font-family: var(--font-mono, ui-monospace, monospace);
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.2);
}

.simulator-header {
  background: rgba(255, 255, 255, 0.02);
  border-bottom: 1px solid var(--border, #222);
  padding: 0.75rem 1.25rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.simulator-dots {
  display: flex;
  gap: 6px;
}

.simulator-dots .dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.simulator-dots .dot.red { background: #ef4444; }
.simulator-dots .dot.yellow { background: #fbbf24; }
.simulator-dots .dot.green { background: #22c55e; }

.simulator-title {
  font-size: 0.8rem;
  color: var(--muted, #666);
}

.simulator-btn {
  margin: 0;
  font-size: 0.8rem;
  padding: 0.4rem 0.9rem;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border, #222);
  color: var(--text, #eee);
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
}

.simulator-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.1);
  border-color: var(--text, #eee);
}

.simulator-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.simulator-body {
  padding: 1.25rem;
  font-size: 0.85rem;
  line-height: 1.6;
  height: 300px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  color: #c9d1d9;
  scroll-behavior: smooth;
}

/* Color Coding Ramps */
.console-line {
  word-break: break-all;
}
.console-line.system { color: #8b949e; }
.console-line.agent { color: #58a6ff; }
.console-line.cmd { color: #58a6ff; font-weight: bold; }
.console-line.gate-pass { color: #34d399; }
.console-line.gate-fail { color: #f85149; }
.console-line.user { color: #fbbf24; }

/* Interactive Prompts */
.console-line.input-prompt {
  color: #ffffff;
  background: rgba(255, 255, 255, 0.02);
  padding: 0.75rem;
  border-radius: 6px;
  border: 1px solid var(--border, #222);
  margin-top: 0.5rem;
  font-family: var(--font-body, system-ui, sans-serif);
}

/* Table structure inside simulator */
.sim-interactive-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.78rem;
  margin: 0.75rem 0;
  font-family: var(--font-mono, ui-monospace, monospace);
}

.sim-interactive-table th, 
.sim-interactive-table td {
  padding: 0.5rem;
  border: 1px solid var(--border, #222);
  text-align: left;
}

.sim-interactive-table th {
  background: rgba(255, 255, 255, 0.02);
  color: var(--muted, #666);
}

.sim-select {
  background: #0d1117;
  color: #ffffff;
  border: 1px solid var(--border, #222);
  border-radius: 4px;
  padding: 0.15rem 0.3rem;
  font-size: 0.75rem;
  outline: none;
  cursor: pointer;
}

.sim-submit-btn {
  background: var(--tier-ultimate, #f59e0b);
  color: #000;
  border: none;
  padding: 0.4rem 0.8rem;
  font-family: var(--font-body, system-ui, sans-serif);
  font-weight: bold;
  border-radius: 4px;
  cursor: pointer;
  margin-top: 0.5rem;
  transition: opacity 0.15s;
}

.sim-submit-btn:hover {
  opacity: 0.9;
}
```

### 3. JavaScript Execution Engine

Use this template to model logs and timeline transitions:

```javascript
(function() {
  const startBtn = document.getElementById("startSimBtn");
  const consoleBox = document.getElementById("simulatorConsole");
  let isRunning = false;

  function addLog(msg, type = "system") {
    const line = document.createElement("div");
    line.className = `console-line ${type}`;
    line.innerHTML = msg;
    consoleBox.appendChild(line);
    consoleBox.scrollTop = consoleBox.scrollHeight;
  }

  if (startBtn && consoleBox) {
    startBtn.addEventListener("click", () => {
      if (isRunning) return;
      isRunning = true;
      startBtn.disabled = true;
      startBtn.innerText = "Running...";
      consoleBox.innerHTML = "";
      
      let currentFrame = 0;

      // Define your timeline frames here
      const timeline = [
        { delay: 400, action: () => addLog("[System] Initiating process...", "system") },
        { delay: 800, action: () => addLog("[CLI] Running `tool --command`", "cmd") },
        { delay: 1200, action: () => addLog("[Agent] Analyzing results...", "agent") },
        
        // Example: Wait for human input (L4 style)
        { 
          delay: 800, 
          action: () => {
            addLog("[System] WAITING FOR HUMAN REVIEW INPUT...", "system");
            
            const promptBox = document.createElement("div");
            promptBox.className = "console-line input-prompt";
            promptBox.innerHTML = `
              <div style="font-weight: bold; margin-bottom: 0.5rem;">Interactive Options:</div>
              <select class="sim-select" id="simUserChoice">
                <option value="yes">Yes, proceed</option>
                <option value="no">No, abort</option>
              </select>
              <button class="sim-submit-btn" id="simSubmitChoice">Submit</button>
            `;
            consoleBox.appendChild(promptBox);
            consoleBox.scrollTop = consoleBox.scrollHeight;

            document.getElementById("simSubmitChoice").addEventListener("click", () => {
              const choice = document.getElementById("simUserChoice").value;
              promptBox.remove();
              addLog(`[User] Choice: <strong>${choice.toUpperCase()}</strong>`, "user");
              
              if (choice === "yes") {
                addLog("[Gate] PASS! Resuming simulation...", "gate-pass");
                currentFrame++;
                runNext();
              } else {
                addLog("[Gate] ABORT! Pipeline halted.", "gate-fail");
                resetSimulator();
              }
            });
          },
          isBlocking: true // Prevents immediate auto-advancing to the next frame
        },

        { delay: 1000, action: () => addLog("[System] Command finished successfully.", "gate-pass") }
      ];

      function runNext() {
        if (currentFrame >= timeline.length) {
          resetSimulator();
          return;
        }

        const frame = timeline[currentFrame];
        setTimeout(() => {
          frame.action();
          if (!frame.isBlocking) {
            currentFrame++;
            runNext();
          }
        }, frame.delay);
      }

      function resetSimulator() {
        startBtn.disabled = false;
        isRunning = false;
        startBtn.innerText = "Run Simulation";
      }

      runNext();
    });
  }
})();
```

---

## Design and Accessibility Standards

When implementing terminal simulations:
1. **Never block user-interaction**: Keep the manual "Run Simulation" trigger. Auto-starting animations on load is jarring and wastes CPU.
2. **Reduced Motion**: Respect system settings. If `@media (prefers-reduced-motion: reduce)` matches, either run the animation instantly (zero delay) or skip the simulation and display the final logs immediately.
3. **Contrast Rules**: Make sure custom log colors (like `.agent`, `.gate-pass`, `.user`) hit at least **4.5:1** contrast ratio against the dark background. Do not use dark blue or dark red text.
4. **No Overflow**: Enforce `word-break: break-all` and `overflow-x: auto` on lines to prevent text clipping on mobile viewports.

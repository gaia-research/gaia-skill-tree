#!/usr/bin/env python3
"""Update Suite Skill Instructions (Surgical & Categorized).

Synchronizes installation instructions for suite skills and their members.
Categorizes skills to provide tailored instructions while preserving 
existing content (Overview, Key Capabilities, etc.).
Ensures adherence to DESIGN.md and Hunter's Atlas branding.
"""

import os
import re
import sys
import urllib.request
from typing import Dict, Optional, List

# Add project root to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# Config for "Super Repos" or special suites
UPSTREAM_CONFIG = {
    "obra/superpowers": {
        "url": "https://raw.githubusercontent.com/obra/superpowers/main/README.md",
        "heading_keywords": ["Installation"],
        "path": "registry/named/obra/superpowers.md"
    },
    "garrytan/gstack": {
        "url": "https://raw.githubusercontent.com/garrytan/gstack/main/README.md",
        "heading_keywords": ["Install", "Quick Start"],
        "path": "registry/named/garrytan/gstack.md"
    },
    "ruvnet/ruflo": {
        "url": "https://raw.githubusercontent.com/ruvnet/ruflo/main/README.md",
        "heading_keywords": ["Quick Start", "Installation"],
        "path": "registry/named/ruvnet/ruflo.md"
    }
}

# Templates
MATT_TEMPLATE = """This skill is included in the Matt Pocock skills suite. It is highly recommended to install the full suite to enable cross-skill context sharing.

```bash
npx skills@latest add mattpocock/skills
```

No additional setup required beyond the main suite installation."""

RUFLO_MEMBER_TEMPLATE = """This skill is part of the Ruflo orchestration platform.

```bash
npx ruflo@latest init
```

See the [Ruflo (ruvnet/ruflo)](../ruvnet/ruflo.md) capstone for full multi-topology installation options."""

def fetch_url(url: str) -> Optional[str]:
    print(f"Fetching {url}...")
    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode('utf-8')
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None

def extract_section(body: str, keywords: List[str]) -> str:
    """Extract section from markdown body matching any of the keywords."""
    for kw in keywords:
        pattern = r'(?:^|\n)##\s+[^\n]*?' + re.escape(kw) + r'[^\n]*?\s*\n(.*?)(?=\n##\s|\Z)'
        m = re.search(pattern, body, re.IGNORECASE | re.DOTALL)
        if m:
            return m.group(1).strip()
    return ""

def standardize_markdown(content: str) -> str:
    """Apply DESIGN.md styling rules."""
    # Enforce bash blocks for untyped blocks
    # Only replace triple backticks that AREN'T followed by a language
    def replace_untyped_blocks(match):
        inner = match.group(1)
        if not inner.strip(): return match.group(0)
        # If it doesn't start with a language identifier (word), add bash
        if not re.match(r'^[a-z]+', inner):
            return "```bash\n" + inner
        return match.group(0)

    # First, handle the common cases
    content = content.replace("```text", "```bash")
    content = content.replace("```shell", "```bash")
    content = content.replace("```sh", "```bash")
    
    # Surgical regex for empty language blocks
    content = re.sub(r'```\s*\n(.*?)(?=\n```)', replace_untyped_blocks, content, flags=re.DOTALL)
    
    # Remove excessive SaaS-style "Congratulations!" padding
    content = re.sub(r'#+\s*(Congratulations|Getting Started|Welcome).*?\n', '', content, flags=re.IGNORECASE)
    
    return content.strip()
def surgical_update(file_path: str, new_install_body: str):
    """Update only the ## Installation section of a file."""
    if not os.path.exists(file_path):
        return

    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()

    if "---" not in text:
        return

    parts = text.split("---", 2)
    if len(parts) < 3:
        return

    header = parts[0] + "---" + parts[1] + "---"
    body = parts[2]

    # Look for ## Installation or ## Install or ## Quick Start to replace
    # We replace until the next ## header at the SAME level (level 2)
    # OR until the end of the file if it's the last section.
    # Note: We specifically look for ## headers to avoid eating ### subheaders
    # if we were already in a subheader (unlikely for installation).
    patterns = [
        r'(?:^|\n)##\s+Installation\s*\n.*?(?=\n##\s|\Z)',
        r'(?:^|\n)##\s+Install\s*\n.*?(?=\n##\s|\Z)',
        r'(?:^|\n)##\s+Quick Start\s*\n.*?(?=\n##\s|\Z)'
    ]

    found = False
    new_body = body
    replacement = f"\n\n## Installation\n\n{new_install_body}\n"

    for p in patterns:
        if re.search(p, new_body, re.IGNORECASE | re.DOTALL):
            new_body = re.sub(p, replacement, new_body, flags=re.IGNORECASE | re.DOTALL)
            found = True
            break

    if not found:
        # Append at the end if no installation section found
        new_body = new_body.rstrip() + replacement

    # Clean up double newlines
    new_body = re.sub(r'\n{3,}', '\n\n', new_body)

    # Prevent doubling if the old file had level 2 headers for things now in level 3
    # e.g., if we now have ### OpenClaw, remove any trailing ## OpenClaw
    new_headers = re.findall(r'^###\s+(.+)$', new_install_body, re.MULTILINE)
    for h in new_headers:
        h_clean = h.strip()
        # Remove any level 2 header that exactly matches a new level 3 header
        dup_pattern = r'\n##\s+' + re.escape(h_clean) + r'\s*\n.*?(?=\n##\s|\Z)'
        new_body = re.sub(dup_pattern, '', new_body, flags=re.IGNORECASE | re.DOTALL)

    final_text = header + new_body
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(final_text)
    print(f"Surgically updated {file_path}")


def main():
    print("Starting surgical suite instruction update...")
    
    # 1. Update Capstones from Upstream
    for suite_id, info in UPSTREAM_CONFIG.items():
        raw_content = fetch_url(info["url"])
        if raw_content:
            section = extract_section(raw_content, info["heading_keywords"])
            if section:
                surgical_update(info["path"], standardize_markdown(section))

    # 2. Iterate all registry files for members
    named_dir = "registry/named"
    for root, _, files in os.walk(named_dir):
        for name in files:
            if not name.endswith(".md"): continue
            fp = os.path.join(root, name)
            with open(fp, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Simple check for suite membership in frontmatter
            if "contributor: mattpocock" in content:
                # If it's a category or individual skill (has suiteRef or is under Category)
                # But NOT the main capstone (already handled)
                if "id: mattpocock/skills" not in content:
                    surgical_update(fp, MATT_TEMPLATE)
            
            elif "suiteRef: ruvnet/ruflo" in content:
                surgical_update(fp, RUFLO_MEMBER_TEMPLATE)

    # 3. Bake changes
    print("Running indexer...")
    os.system(f"{sys.executable} scripts/generateNamedIndex.py")
    print("Done.")

if __name__ == "__main__":
    main()

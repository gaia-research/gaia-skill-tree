import os
import re
import subprocess
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

scriptDir = os.path.dirname(os.path.abspath(__file__))
lakeDir = os.path.abspath(os.path.join(scriptDir, ".."))
files = sorted([fname for fname in os.listdir(lakeDir) if fname.endswith(".md") and fname.startswith("tier_")])

urlPattern = re.compile(r'\[.*?\]\((https?://.*?)\)')

# Map from URL to list of (filename, lineNum, skillId)
urlOccurrences = {}

for fname in files:
    fpath = os.path.join(lakeDir, fname)
    with open(fpath, "r", encoding="utf-8") as f:
        currentSkill = "Unknown"
        for lineNum, line in enumerate(f, 1):
            if line.startswith("## Skill:"):
                m = re.match(r'## Skill:\s*`(.*?)`', line)
                if m:
                    currentSkill = m.group(1)
            
            matches = urlPattern.findall(line)
            for url in matches:
                url = url.strip()
                if url not in urlOccurrences:
                    urlOccurrences[url] = []
                urlOccurrences[url].append((fname, lineNum, currentSkill))

uniqueUrls = sorted(list(urlOccurrences.keys()))
print(f"Total unique URLs found: {len(uniqueUrls)}")

# Check for limit argument for quick test
limit = None
if len(sys.argv) > 1:
    try:
        limit = int(sys.argv[1])
        print(f"Limiting validation to first {limit} URLs for testing.")
        uniqueUrls = uniqueUrls[:limit]
    except ValueError:
        pass

results = {}

def validateUrl(url):
    try:
        # Run firecrawl scrape --json <url>
        cmd = ["firecrawl", "scrape", url, "--json"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if proc.returncode != 0:
            return url, {"status": "error", "message": f"CLI error (exit code {proc.returncode}): {proc.stderr.strip()[:150]}"}
        
        output = proc.stdout.strip()
        jsonStart = output.find('{')
        if jsonStart == -1:
            return url, {"status": "error", "message": f"No JSON in output: {output[:150]}"}
        
        try:
            data = json.loads(output[jsonStart:])
        except json.JSONDecodeError as je:
            return url, {"status": "error", "message": f"JSON decode error: {str(je)} output: {output[:100]}"}
        
        statusCode = data.get("statusCode", 200)
        error = data.get("error")
        
        if statusCode == 404 or error == "Not Found":
            return url, {"status": "broken", "statusCode": statusCode, "error": error or "Not Found"}
        else:
            return url, {"status": "ok", "statusCode": statusCode}
            
    except Exception as e:
        return url, {"status": "error", "message": str(e)}

print("Starting validation using Firecrawl (concurrency=2)...")
completed = 0
with ThreadPoolExecutor(max_workers=2) as executor:
    futures = {executor.submit(validateUrl, url): url for url in uniqueUrls}
    for future in as_completed(futures):
        url = futures[future]
        try:
            url, res = future.result()
            results[url] = res
            completed += 1
            if res["status"] == "broken":
                print(f"[{completed}/{len(uniqueUrls)}] ❌ BROKEN: {url} -> {res.get('statusCode')} {res.get('error')}")
            elif res["status"] == "error":
                print(f"[{completed}/{len(uniqueUrls)}] ⚠ ERROR: {url} -> {res.get('message')}")
            else:
                print(f"[{completed}/{len(uniqueUrls)}] ✓ OK: {url}")
        except Exception as e:
            completed += 1
            print(f"[{completed}/{len(uniqueUrls)}] 💥 EXCEPTION: {url} -> {str(e)}")

# Save report
reportPath = os.path.join(lakeDir, "data_lake_validation_report.md")
with open(reportPath, "w", encoding="utf-8") as f:
    f.write("# Data Lake Source Validation Report\n\n")
    f.write(f"Validated {len(uniqueUrls)} URLs using Firecrawl.\n\n")
    
    f.write("## Broken Links\n\n")
    f.write("| Skill ID | File | Line | URL | Status |\n")
    f.write("| --- | --- | --- | --- | --- |\n")
    brokenCount = 0
    for url, res in sorted(results.items()):
        if res["status"] == "broken":
            brokenCount += 1
            for fname, lineNum, skillId in urlOccurrences[url]:
                f.write(f"| `{skillId}` | `{fname}` | {lineNum} | {url} | {res.get('statusCode')} {res.get('error')} |\n")
                
    f.write(f"\nTotal broken links: {brokenCount}\n\n")
    
    f.write("## Validation Errors (CLI/API Issues)\n\n")
    f.write("| URL | Error Message |\n")
    f.write("| --- | --- |\n")
    errCount = 0
    for url, res in sorted(results.items()):
        if res["status"] == "error":
            errCount += 1
            f.write(f"| {url} | {res.get('message')} |\n")
            
    f.write(f"\nTotal validation errors: {errCount}\n\n")
    
    f.write("## Valid Links\n\n")
    f.write("| URL | Status |\n")
    f.write("| --- | --- |\n")
    for url, res in sorted(results.items()):
        if res["status"] == "ok":
            f.write(f"| {url} | {res.get('statusCode')} |\n")

print(f"\nValidation complete. Report written to {reportPath}")

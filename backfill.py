import subprocess
from pathlib import Path
from datetime import datetime, timezone
import sys
sys.path.insert(0, str(Path().resolve()))
import scripts.contentEngine.generate_weekly_report as rep

tasks = [
    ("40ee25000295ed909a491b01a8f9900a018e63a3", datetime(2026, 7, 13, 8, 0, 0, tzinfo=timezone.utc)),
    ("f73e7d57937ca90e7e0814e6e0e9403757e341d0", datetime(2026, 7, 20, 8, 0, 0, tzinfo=timezone.utc)),
    ("c6c7cc78ed457eec3ab72035f03b2a7a05278fce", datetime(2026, 7, 27, 8, 0, 0, tzinfo=timezone.utc)),
]

for commit, dt in tasks:
    print(f"Checking out trending for {dt.strftime('%Y-%m-%d')} at commit {commit[:7]}...")
    subprocess.run(["git", "checkout", commit, "--", "docs/api/v1/trending"], check=True)
    
    print(f"Generating report for {dt.strftime('%Y-%m-%d')}...")
    rep.run(
        apiDir=Path('docs/api/v1'),
        docsRoot=Path('docs'),
        publishFlag=True,
        now=dt
    )

print("Restoring latest trending...")
subprocess.run(["git", "checkout", "origin/main", "--", "docs/api/v1/trending"], check=True)
print("Done!")

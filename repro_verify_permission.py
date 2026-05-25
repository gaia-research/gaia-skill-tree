
import subprocess
import sys
import os
import json
from pathlib import Path

def run_command(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result

def test_verify_permission():
    # 1. Setup a dummy registry
    reg_path = Path("temp_registry")
    reg_path.mkdir(exist_ok=True)
    
    named_dir = reg_path / "registry" / "named"
    named_dir.mkdir(parents=True, exist_ok=True)
    
    # Create named skills index
    index = {
        "buckets": {
            "test": [
                {"id": "test/skill", "contributor": "verifier_user", "level": "4★"},
                {"id": "test/low", "contributor": "normal_user", "level": "2★"}
            ]
        }
    }
    with open(named_dir / "index.json", "w") as f:
        json.dump(index, f)

    # 2. Mock config to be "normal_user"
    config_path = Path.home() / ".gaia" / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    old_config = None
    if config_path.exists():
        old_config = config_path.read_text()
    
    try:
        with open(config_path, "w") as f:
            json.dump({"username": "normal_user"}, f)
        
        # 3. Try to verify (should fail)
        # We need a skill to verify.
        skill_file = named_dir / "test" / "low.md"
        skill_file.parent.mkdir(parents=True, exist_ok=True)
        skill_file.write_text("---\nid: test/low\nevidence:\n  - class: C\n    source: http://example.com\n    evaluator: normal_user\n    date: '2023-01-01'\n---\nBody")
        
        res = run_command(f"python3 -m gaia_cli.main --registry {reg_path} dev verify test/low --index 0")
        print("Output:", res.stdout)
        print("Error:", res.stderr)
        
        if res.returncode != 0 and "not a Verifier" in res.stdout:
            print("RED TEST PASSED: Non-verifier rejected.")
        else:
            print("RED TEST FAILED: Non-verifier was NOT rejected correctly.")
            sys.exit(1)

        # 4. Mock config to be "verifier_user"
        with open(config_path, "w") as f:
            json.dump({"username": "verifier_user"}, f)
            
        # 5. Try to verify (should succeed)
        res = run_command(f"python3 -m gaia_cli.main --registry {reg_path} dev verify test/low --index 0 --no-build")
        print("Output:", res.stdout)
        print("Error:", res.stderr)
        
        if res.returncode == 0 and "Verified evidence" in res.stdout:
            print("GREEN TEST PASSED: Verifier accepted.")
        else:
            print("GREEN TEST FAILED: Verifier was rejected.")
            sys.exit(1)
            
    finally:
        # Cleanup
        if old_config:
            config_path.write_text(old_config)
        else:
            config_path.unlink()
        import shutil
        shutil.rmtree(reg_path)

if __name__ == "__main__":
    test_verify_permission()

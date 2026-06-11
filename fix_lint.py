with open("src/gaia_cli/semantic_search.py", "r") as f:
    lines = f.readlines()

has_import_math = any(line.strip() == "import math" for line in lines)
print(f"has_import_math: {has_import_math}")

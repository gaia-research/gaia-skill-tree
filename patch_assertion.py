import sys

with open('tests/test_packaging.py', 'r') as f:
    content = f.read()

content = content.replace(
    'assert (gaia_home / "skills" / "alice" / "skill.md").exists()',
    'assert (gaia_home / "skills" / "alice" / "repo").exists()'
)

with open('tests/test_packaging.py', 'w') as f:
    f.write(content)


import argparse
import sys
from pathlib import Path
from gaia_cli.commands import mcp_cmd
args = argparse.Namespace(mcp_command="status", registry=Path("/Users/marcotiongson/Documents/gaia-skill-tree"))
mcp_cmd.execute_dev_mcp(args)
print("DONE")

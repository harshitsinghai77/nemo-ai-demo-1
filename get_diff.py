import subprocess
import re
import os
import json
from typing import List, Dict, Any


def run_cmd(cmd: list[str]) -> str:
    result = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True
    )
    return result.stdout.strip()


def parse_diff(diff_text: str, change_type: str) -> List[Dict[str, Any]]:
    """Parse git diff output into structured entries."""
    changes = []
    current_file = None

    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif line.startswith("@@") and current_file:
            match = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if match:
                start_line = int(match.group(1))
                length = int(match.group(2) or 1)
                end_line = start_line + length - 1
                changes.append({
                    "file_path": f"./{current_file}",
                    "change_type": change_type,
                    "mode": "lines",
                    "start_line": start_line,
                    "end_line": end_line
                })
    return changes


def get_untracked_files() -> List[Dict[str, Any]]:
    """Return untracked files as manifest entries."""
    out = run_cmd(["git", "ls-files", "--others", "--exclude-standard"])
    files = out.splitlines() if out else []
    entries = []
    for f in files:
        if os.path.isfile(f):
            with open(f, "r", encoding="utf-8", errors="ignore") as fh:
                num_lines = sum(1 for _ in fh)
            entries.append({
                "file_path": f"./{f}",
                "change_type": "untracked_file",
                "mode": "full",
                "start_line": 1,
                "end_line": num_lines
            })
    return entries


if __name__ == "__main__":
    manifest = {"changes": []}

    # Modified tracked files (unstaged)
    uncommitted = run_cmd(["git", "diff", "--unified=0"])
    manifest["changes"].extend(parse_diff(uncommitted, "modified_file"))

    # Staged changes (including new files already added)
    staged = run_cmd(["git", "diff", "--cached", "--unified=0"])
    manifest["changes"].extend(parse_diff(staged, "staged_new_file"))

    # Untracked files
    manifest["changes"].extend(get_untracked_files())
    
    manifest["changes"] = [c for c in manifest["changes"] if c["file_path"].endswith(".py")]
    print(json.dumps(manifest, indent=2))

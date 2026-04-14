"""
Scaffolds a standard GEMINI.md for a target project.
"""

import argparse
from pathlib import Path
import utils

def init_project(workspace: str):
    workspace_path = Path(workspace)
    gemini_path = workspace_path / "GEMINI.md"
    
    if gemini_path.exists():
        print(f"Project already has a GEMINI.md at {gemini_path}")
        return

    content = """# Project Brain: [Project Name]

## Architectural Invariants
- Maintain strict Logic/View separation.
- [Add more invariants here...]

## QA Rituals & Testing
- Ritual 1: Always verify success.txt exists.
- [Add more rituals here...]
"""
    workspace_path.mkdir(parents=True, exist_ok=True)
    with open(gemini_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Scaffolded Project Prompting (Layer 3) at {gemini_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize Project Brain")
    parser.add_argument("workspace")
    args = parser.parse_args()
    init_project(args.workspace)

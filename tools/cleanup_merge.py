"""
Cleanup tool for the Developer OS. 
Removes execution artifacts and prepares for merging into main.
"""

import argparse
import subprocess
import os

def cleanup_branch(workspace: str):
    """Removes artifacts and commits the cleanup."""
    artifacts = ["IRQ.md", "QAR.md", "IRP.md", "QRP.md"]
    to_remove = []
    for art in artifacts:
        if os.path.exists(os.path.join(workspace, art)):
            to_remove.append(art)
    
    if not to_remove:
        print("No artifacts found to clean up.")
        return

    print(f"[CLEANUP] Removing artifacts: {', '.join(to_remove)}")
    subprocess.run(["git", "rm"] + to_remove, cwd=workspace, check=True)
    subprocess.run(["git", "commit", "-m", "chore: remove execution artifacts"], cwd=workspace, check=True)
    
    # Get current branch
    res = subprocess.run(["git", "branch", "--show-current"], cwd=workspace, capture_output=True, text=True, check=True)
    current_branch = res.stdout.strip()
    
    print(f"\nCleanup complete on branch '{current_branch}'.")
    print(f"To merge into main, run:")
    print(f"  git checkout main")
    print(f"  git merge --squash {current_branch}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cleanup Execution Artifacts")
    parser.add_argument("workspace", help="Path to the project workspace")
    args = parser.parse_args()
    cleanup_branch(args.workspace)

"""
Common utility functions and paths for the Developer OS.
"""

import os
import sys
import subprocess
from pathlib import Path

# Absolute Pathing
TOOLS_DIR = Path(__file__).parent
REPO_ROOT = TOOLS_DIR.parent
TEMPLATES_DIR = REPO_ROOT / "templates" / "artifacts"
ROLES_DIR = REPO_ROOT / "templates" / "roles"
IMPLEMENTATION_SCRIPT = REPO_ROOT / "implementation_run.py"

def run_loop_cmd(workspace: str, git_gate: bool = False, run_id: str = None):
    """Triggers the headless Doer/QA loop."""
    cmd = [sys.executable, str(IMPLEMENTATION_SCRIPT), "--workspace", workspace]
    if git_gate:
        cmd.append("--git-gate")
    if run_id:
        cmd.extend(["--run-id", run_id])
        
    print(f"[ORCHESTRATOR] Dispatching headless workers in {workspace}...")
    subprocess.run(cmd)

# --- Git State Machine Helpers ---

def is_git_clean(workspace: str) -> bool:
    try:
        res = subprocess.run(["git", "status", "--porcelain"], cwd=workspace, capture_output=True, text=True, check=True)
        return res.stdout.strip() == ""
    except Exception:
        return True # Not a git repo or git not found

def git_checkout_branch(workspace: str, branch_name: str):
    subprocess.run(["git", "checkout", "-b", branch_name], cwd=workspace, check=True)

def git_commit_all(workspace: str, message: str):
    subprocess.run(["git", "add", "."], cwd=workspace, check=True)
    # Use --allow-empty in case no changes were made (e.g. QA just approved without code change)
    subprocess.run(["git", "commit", "--allow-empty", "-m", message], cwd=workspace, check=True)

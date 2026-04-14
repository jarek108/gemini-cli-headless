"""
Automated dispatch: Headless Manager drafts contracts and triggers the loop.
"""

import sys
import argparse
import time
from pathlib import Path
import utils

# Add repo root to path for gemini_cli_headless
sys.path.append(str(utils.REPO_ROOT))
from gemini_cli_headless import run_gemini_cli_headless

def implement_feature(workspace: str, summary: str, git_gate: bool = False, model_id: str = "gemini-3-flash-preview"):
    workspace_path = Path(workspace)
    
    # 0. Git Branching & Gating
    run_id = f"run_{int(time.time())}"
    if not utils.is_git_clean(workspace):
        if git_gate:
            print(f"ERROR: Workspace is not clean. Commit or stash changes before running.")
            return
        else:
            print(f"[WARNING] Workspace is not clean. Continuing on current branch.")
    else:
        branch_name = f"gemini-{run_id}"
        print(f"[GIT] Creating new feature branch: {branch_name}")
        utils.git_checkout_branch(workspace, branch_name)

    # 1. Load Context
    gemini_path = workspace_path / "GEMINI.md"
    project_context = ""
    if gemini_path.exists():
        with open(gemini_path, 'r', encoding='utf-8') as f:
            project_context = f.read()

    # 2. Load Templates & Prompt
    with open(utils.ROLES_DIR / "manager_headless_prompt.md", 'r', encoding='utf-8') as f:
        prompt_tmpl = f.read()
    with open(utils.TEMPLATES_DIR / "irq_template.md", 'r', encoding='utf-8') as f:
        irq_tmpl = f.read()
    with open(utils.TEMPLATES_DIR / "qar_template.md", 'r', encoding='utf-8') as f:
        qar_tmpl = f.read()

    # 3. Build Full Prompt for Headless Manager
    full_prompt = prompt_tmpl.replace("{{compiled_intent}}", summary)
    full_prompt = full_prompt.replace("{{project_context}}", project_context)
    full_prompt += f"\n\n### Reference Templates\n<irq_template>\n{irq_tmpl}\n</irq_template>\n\n<qar_template>\n{qar_tmpl}\n</qar_template>"

    print(f"[MANAGER: HEADLESS] Compiling intent into Space-Grade Specs...")
    
    # 4. Execute Headless Manager
    try:
        session = run_gemini_cli_headless(
            prompt=full_prompt,
            model_id=model_id,
            cwd=workspace
        )
    except Exception as e:
        print(f"ERROR: Headless Manager failed: {e}")
        return

    # 5. Verify Artifacts & Commit Genesis
    if (workspace_path / "IRQ.md").exists() and (workspace_path / "QAR.md").exists():
        print(f"[MANAGER: HEADLESS] Paperwork filed successfully. Committing specs.")
        utils.git_commit_all(workspace, "[MANAGER] Drafted Space-Grade Specifications")
        utils.run_loop_cmd(workspace, git_gate, run_id=run_id)
    else:
        print(f"ERROR: Headless Manager failed to produce IRQ.md and QAR.md.")
        print(f"\nLast response from manager:\n{session.text[:500]}...")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Dispatch Automated Feature Implementation")
    parser.add_argument("workspace")
    parser.add_argument("--summary", required=True)
    parser.add_argument("--git-gate", action="store_true")
    parser.add_argument("--model", default="gemini-3-flash-preview")
    args = parser.parse_args()
    
    implement_feature(args.workspace, args.summary, args.git_gate, args.model)

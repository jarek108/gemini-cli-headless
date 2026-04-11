"""
End-to-End Test Runner for Gemini CLI Headless Orchestrator.
Discovers and executes data-driven test cases from the e2e_cases/ directory.
"""

import os
import json
import shutil
import zipfile
import subprocess
import sys
import time
import argparse
from typing import List, Dict

# Color coding for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

def run_case(case_path: str, runner_script: str, keep_workspace: bool) -> bool:
    case_name = os.path.basename(case_path)
    print(f"\n[TEST CASE] {case_name}")
    
    # 1. Setup temporary workspace
    workspace = os.path.join(os.getcwd(), f"temp_workspace_{case_name}")
    if os.path.exists(workspace):
        shutil.rmtree(workspace)
    os.makedirs(workspace)

    try:
        # 2. Extract initial state if zip exists
        zip_path = os.path.join(case_path, "initial_state.zip")
        if os.path.exists(zip_path):
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(workspace)
        
        # 3. Copy IRQ.md
        shutil.copy2(os.path.join(case_path, "IRQ.md"), os.path.join(workspace, "IRQ.md"))
        
        # 4. Load config
        with open(os.path.join(case_path, "config.json"), 'r') as f:
            cfg = json.load(f)
            
        # 5. Execute implementation_run.py
        cmd = [
            sys.executable, runner_script,
            "--workspace", workspace,
            "--max-iters", str(cfg.get("max_iters", 3)),
            "--doer-model", cfg.get("doer_model", "gemini-1.5-flash"),
            "--qa-model", cfg.get("qa_model", "gemini-1.5-flash")
        ]
        
        print(f"  > Executing {case_name}...")
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8')
        
        # 6. Common Assertions
        state_path = os.path.join(workspace, "run_state.json")
        success = True
        errors = []

        if not os.path.exists(state_path):
            success = False
            errors.append("run_state.json not found")
        else:
            with open(state_path, 'r') as f:
                state = json.load(f)
            if state.get("status") != "SUCCESS":
                success = False
                errors.append(f"Status is {state.get('status')} instead of SUCCESS")

        # Check for IRP and QRP artifacts
        iters = state.get("iteration", 0) if os.path.exists(state_path) else 0
        if iters > 0:
            if not os.path.exists(os.path.join(workspace, f"IRP_v{iters}.md")):
                success = False
                errors.append(f"Missing IRP_v{iters}.md artifact")
            
            qrp_path = os.path.join(workspace, f"QRP_v{iters}.md")
            if not os.path.exists(qrp_path):
                success = False
                errors.append(f"Missing QRP_v{iters}.md artifact")
            else:
                with open(qrp_path, 'r') as f:
                    if "[STATUS: APPROVED]" not in f.readline():
                        success = False
                        errors.append("QA Report is not APPROVED")

        if success:
            print(f"  {GREEN}[PASS]{RESET} {case_name}")
            return True
        else:
            print(f"  {RED}[FAIL]{RESET} {case_name}")
            for err in errors:
                print(f"    - {err}")
            if result.stderr:
                print(f"    --- STDERR ---\n{result.stderr}")
            return False

    finally:
        if not keep_workspace and os.path.exists(workspace):
            shutil.rmtree(workspace)

def main():
    parser = argparse.ArgumentParser(description="Run E2E agent tests")
    parser.add_argument("--cases-dir", default="./tests/e2e_cases", help="Directory with test cases")
    parser.add_argument("--keep", action="store_true", help="Keep workspaces after test for inspection")
    args = parser.parse_args()

    # Root of the repo is one level up from here (if inside tests/)
    # But usually we run from root.
    base_dir = os.path.abspath(os.getcwd())
    runner_script = os.path.join(base_dir, "implementation_run.py")
    
    if not os.path.exists(runner_script):
        print(f"Error: Could not find {runner_script}")
        sys.exit(1)

    cases_dir = os.path.abspath(args.cases_dir)
    if not os.path.exists(cases_dir):
        print(f"Error: Cases directory {cases_dir} not found")
        sys.exit(1)

    # Load .env fallback from FDDS if present for convenience
    fdds_env = os.path.abspath(os.path.join(base_dir, "../fdds/config/.env"))
    if os.path.exists(fdds_env) and not os.environ.get("GEMINI_API_KEY"):
        from dotenv import load_dotenv
        load_dotenv(fdds_env)
        print(f"Loaded API Key from {fdds_env}")

    cases = [os.path.join(cases_dir, d) for d in os.listdir(cases_dir) if os.path.isdir(os.path.join(cases_dir, d))]
    cases.sort()

    passed = 0
    total = len(cases)

    for case in cases:
        if run_case(case, runner_script, args.keep):
            passed += 1

    print(f"\n{'='*40}")
    print(f"E2E TEST SUMMARY: {passed}/{total} PASSED")
    print(f"{'='*40}")

    if passed != total:
        sys.exit(1)

if __name__ == "__main__":
    main()

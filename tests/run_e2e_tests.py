"""
End-to-End Test Runner for Gemini CLI Headless Orchestrator v2.
"""

import os
import json
import shutil
import zipfile
import subprocess
import sys
import time
import argparse
from pathlib import Path
from typing import List, Dict

# Color coding for terminal output
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

def run_case(case_path: str, runner_script: str, keep_workspace: bool) -> bool:
    case_name = os.path.basename(case_path)
    print(f"\n[TEST CASE] {case_name}")
    
    # 1. Setup temporary workspace and registry inside the case folder
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    workspace = os.path.join(case_path, "temp_workspace", timestamp)
    registry_base = os.path.join(case_path, "temp_registry", timestamp)
    os.makedirs(workspace, exist_ok=True)
    os.makedirs(registry_base, exist_ok=True)

    try:
        # 2. Extract initial state if zip exists
        zip_path = os.path.join(case_path, "initial_state.zip")
        if os.path.exists(zip_path):
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(workspace)
        
        # 3. Copy IRQ.md
        shutil.copy2(os.path.join(case_path, "IRQ.md"), os.path.join(workspace, "IRQ.md"))
        
        # 4. Load config
        config_file = os.path.join(case_path, "config.json")
            
        # 5. Execute implementation_run.py
        env = os.environ.copy()
        
        cmd = [
            sys.executable, runner_script,
            "--workspace", workspace,
            "--config-file", config_file,
            "--registry-base", registry_base
        ]
        
        print(f"  > Executing {case_name} (Registry: {registry_base})...")
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', env=env)
        
        # 6. Discover the actual run directory in registry (it's timestamped)
        runs = os.listdir(registry_base)
        if not runs:
            print(f"  {RED}[FAIL]{RESET} {case_name}: No run directory created in registry")
            return False
            
        run_dir = os.path.join(registry_base, runs[0])
        state_path = os.path.join(run_dir, "run_state.json")
        artifacts_dir = os.path.join(run_dir, "artifacts")
        
        success = True
        errors = []

        if not os.path.exists(state_path):
            success = False
            errors.append("run_state.json not found in registry")
        else:
            with open(state_path, 'r') as f:
                state = json.load(f)
            if state.get("status") != "SUCCESS":
                success = False
                errors.append(f"Status is {state.get('status')} instead of SUCCESS")

        # Check for artifacts in Registry
        iters = state.get("iteration", 0) if os.path.exists(state_path) else 0
        if iters > 0:
            if not os.path.exists(os.path.join(artifacts_dir, f"v{iters}_IRP.md")):
                success = False
                errors.append(f"Missing v{iters}_IRP.md in registry")
            
            qrp_path = os.path.join(artifacts_dir, f"v{iters}_QRP.md")
            if not os.path.exists(qrp_path):
                success = False
                errors.append(f"Missing v{iters}_QRP.md in registry")
            else:
                with open(qrp_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if "outcome: final" not in content.lower():
                        success = False
                        errors.append("QA Report outcome is not 'final'")

        if success:
            print(f"  {GREEN}[PASS]{RESET} {case_name}")
            return True
        else:
            print(f"  {RED}[FAIL]{RESET} {case_name}")
            for err in errors:
                print(f"    - {err}")
            if result.stdout:
                print(f"    --- STDOUT ---\n{result.stdout[-1000:]}")
            if result.stderr:
                print(f"    --- STDERR ---\n{result.stderr}")
            return False

    finally:
        if not keep_workspace:
            if os.path.exists(workspace): shutil.rmtree(workspace)
            if os.path.exists(registry_base): shutil.rmtree(registry_base)

def main():
    parser = argparse.ArgumentParser(description="Run E2E agent tests v2")
    parser.add_argument("--cases-dir", default="./tests/e2e_cases", help="Directory with test cases")
    parser.add_argument("--keep", action="store_true", help="Keep workspaces after test for inspection")
    args = parser.parse_args()

    base_dir = os.path.abspath(os.getcwd())
    runner_script = os.path.join(base_dir, "implementation_run.py")
    cases_dir = os.path.abspath(args.cases_dir)

    # Load .env fallback
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
    if passed != total: sys.exit(1)

if __name__ == "__main__":
    main()

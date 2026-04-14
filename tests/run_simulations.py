"""
Generic Simulation E2E Runner for Gemini CLI Headless.
Validates the system protocol (Roles -> Artifacts -> Project context) using a data-driven approach.
"""

import os
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Add project root to sys.path to ensure local library is used
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from gemini_cli_headless import run_gemini_cli_headless

# Configuration
SIMULATIONS_DIR = Path("./tests/simulations")
SANDBOX_BASE = Path("./tests/simulation_sandboxes")
REGISTRY_BASE = Path(os.path.expanduser("~")) / ".gemini" / "orchestrator" / "runs"
MANAGER_PROMPT_SOURCE = Path("C:/Users/chojn/projects/GEMINI.md")

# Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"

def get_latest_run_id():
    """Returns the most recent run ID from the registry."""
    if not REGISTRY_BASE.exists():
        print(f"  [DEBUG] Registry base does not exist: {REGISTRY_BASE}")
        return None
    runs = [d for d in os.listdir(REGISTRY_BASE) if os.path.isdir(REGISTRY_BASE / d)]
    if not runs:
        return None
    # Sort by timestamp in folder name (run_12345678)
    try:
        runs.sort(key=lambda x: int(x.split('_')[1]) if '_' in x else 0, reverse=True)
    except Exception as e:
        print(f"  [DEBUG] Error sorting runs: {e}")
    return runs[0]

import stat

def remove_readonly(func, path, _):
    """Clear the readonly bit and reattempt the file removal."""
    os.chmod(path, stat.S_IWRITE)
    func(path)

def run_simulation(case_path: Path):
    case_name = case_path.name
    sandbox = SANDBOX_BASE / case_name
    
    print(f"\n{BLUE}=== SIMULATION: {case_name} ==={RESET}")
    
    # 1. Setup Sandbox
    if sandbox.exists():
        shutil.rmtree(sandbox, onerror=remove_readonly)
    os.makedirs(sandbox, exist_ok=True)
    
    # 1.1 Initialize Git
    subprocess.run(["git", "init"], cwd=sandbox, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "sim@test.com"], cwd=sandbox, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.name", "Simulation"], cwd=sandbox, capture_output=True, check=True)
    
    # Genesis commit for the repo itself
    (sandbox / "README.md").write_text("# Simulation Sandbox")
    subprocess.run(["git", "add", "."], cwd=sandbox, check=True)
    subprocess.run(["git", "commit", "-m", "initial commit"], cwd=sandbox, check=True)
    
    # 2. Deploy Manager Prompt
    if MANAGER_PROMPT_SOURCE.exists():
        shutil.copy2(MANAGER_PROMPT_SOURCE, sandbox / "GEMINI.md")
    
    # 3. Deploy Initial Project State
    initial_state_path = case_path / "initial_state"
    if initial_state_path.exists():
        for item in os.listdir(initial_state_path):
            s = initial_state_path / item
            d = sandbox / item
            if s.is_dir():
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
    
    # 3.1 Commit Initial State
    subprocess.run(["git", "add", "."], cwd=sandbox, check=True)
    subprocess.run(["git", "commit", "-m", "deploy initial state"], cwd=sandbox, check=True)
                
    # 4. Read User Prompt
    with open(case_path / "input_prompt.txt", 'r', encoding='utf-8') as f:
        user_prompt = f.read().strip()

    # 5. Execute Manager CLI
    print(f"{YELLOW}[PHASE: MANAGER]{RESET} Executing interaction...")
    start_time = time.time()
    try:
        session = run_gemini_cli_headless(
            prompt=user_prompt,
            cwd=str(sandbox),
            model_id="gemini-3-flash-preview",
            stream_output=True
        )
        print(f"\n{YELLOW}[MANAGER RESPONSE]{RESET}\n{session.text[:500]}...\n")

    except Exception as e:
        print(f"{RED}[FAIL]{RESET} Manager execution failed: {e}")
        return False

    # 6. Verification
    print(f"{YELLOW}[PHASE: VERIFICATION]{RESET} Checking Git Time-Travel invariants...")
    
    errors = []
    
    # A. Branch Check
    try:
        res = subprocess.run(["git", "branch", "--show-current"], cwd=sandbox, capture_output=True, text=True, check=True)
        current_branch = res.stdout.strip()
        if not current_branch.startswith("gemini-run_"):
            errors.append(f"Not on a gemini-run branch. Current: {current_branch}")
        else:
            print(f"  [+] On feature branch: {current_branch}")
    except Exception as e:
        errors.append(f"Failed to check git branch: {e}")

    # B. Commit History Check
    try:
        res = subprocess.run(["git", "log", "--oneline", "-n", "10"], cwd=sandbox, capture_output=True, text=True, check=True)
        history = res.stdout
        print(f"  [DEBUG] Git history:\n{history}")
        
        required_commits = ["[MANAGER] Drafted Space-Grade Specifications", "[DOER]", "[QA]"]
        for msg in required_commits:
            if msg not in history:
                errors.append(f"Missing commit in history: {msg}")
            else:
                print(f"  [+] Found commit: {msg}")
    except Exception as e:
        errors.append(f"Failed to check git history: {e}")

    # C. Artifact Persistence Check
    artifacts = ["IRQ.md", "QAR.md", "IRP.md", "QRP.md"]
    found_any = False
    for root, dirs, files in os.walk(sandbox):
        if ".git" in dirs: dirs.remove(".git")
        for art in artifacts:
            if art in files:
                print(f"  [+] Found artifact: {os.path.join(root, art)}")
                found_any = True
    
    if not found_any:
        errors.append("No execution artifacts found in workspace.")

    # D. Registry Check (Telemetry)
    latest_run = get_latest_run_id()
    if not latest_run:
        errors.append("No run directory found in Central Registry.")
    else:
        run_path = REGISTRY_BASE / latest_run
        print(f"  [+] Found Telemetry in Registry: {latest_run}")
        
        # E. Terminal State Check
        state_file = run_path / "run_state.json"
        if not state_file.exists():
            errors.append("Missing run_state.json in registry.")
        else:
            with open(state_file, 'r') as f:
                state = json.load(f)
            status = state.get("status")
            print(f"  [+] Terminal Status: {status}")
            if status == "PENDING":
                errors.append("Registry status is still PENDING.")

    if not errors:
        print(f"{GREEN}[PASS]{RESET} {case_name} followed the Git-Native protocol.")
        return True
    else:
        print(f"{RED}[FAIL]{RESET} {case_name} protocol violations:")
        for err in errors:
            print(f"    - {err}")
        return False

def main():
    # Ensure API Key
    if not os.environ.get("GEMINI_API_KEY"):
        from dotenv import load_dotenv
        load_dotenv("C:/Users/chojn/projects/fdds/config/.env")

    if not SIMULATIONS_DIR.exists():
        print(f"Error: {SIMULATIONS_DIR} not found.")
        sys.exit(1)

    cases = sorted([d for d in os.listdir(SIMULATIONS_DIR) if (SIMULATIONS_DIR / d).is_dir()])
    
    results = []
    for case in cases:
        success = run_simulation(SIMULATIONS_DIR / case)
        results.append((case, success))

    print(f"\n{'='*40}")
    print(f"SIMULATION SUMMARY:")
    passed = 0
    for name, success in results:
        status = f"{GREEN}PASS{RESET}" if success else f"{RED}FAIL{RESET}"
        print(f"  {name}: {status}")
        if success: passed += 1
    print(f"{'='*40}")
    print(f"TOTAL: {passed}/{len(results)} PASSED")

if __name__ == "__main__":
    main()

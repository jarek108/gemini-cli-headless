"""
Autonomous Implementation Orchestrator v2 (Git-Native State Machine)
"""

import os
import json
import shutil
import time
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
from gemini_cli_headless import run_gemini_cli_headless, GeminiSession

# --- Constants & Defaults ---

DEFAULT_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
DEFAULT_REGISTRY_BASE = os.path.join(str(Path.home()), ".gemini", "orchestrator", "runs")

PRICING = {
    "gemini-1.5-pro": {"input": 3.50, "output": 10.50, "cached": 0.875},
    "gemini-1.5-flash": {"input": 0.075, "output": 0.30, "cached": 0.01875},
    "gemini-3.1-pro": {"input": 3.50, "output": 10.50, "cached": 0.875},
    "gemini-3.1-flash": {"input": 0.075, "output": 0.30, "cached": 0.01875},
    "gemini-3-pro": {"input": 3.50, "output": 10.50, "cached": 0.875},
    "gemini-3-flash": {"input": 0.075, "output": 0.30, "cached": 0.01875}
}

# --- Git Helpers ---

def git_commit(workspace: str, message: str):
    try:
        subprocess.run(["git", "add", "."], cwd=workspace, check=True)
        subprocess.run(["git", "commit", "--allow-empty", "-m", message], cwd=workspace, check=True)
    except Exception as e:
        print(f"[WARNING] Git commit failed: {e}")

# --- Cost Calculation ---

def calculate_cost(model_name: str, input_tokens: int, output_tokens: int, cached_tokens: int = 0) -> float:
    cost = 0.0
    price_key = None
    for k in PRICING.keys():
        if k in model_name:
            price_key = k
            break
    if not price_key:
        if "pro" in model_name.lower(): price_key = "gemini-3.1-pro"
        elif "flash" in model_name.lower(): price_key = "gemini-3.1-flash"

    if price_key:
        p = PRICING[price_key]
        cost = (input_tokens / 1_000_000 * p["input"]) + \
               (output_tokens / 1_000_000 * p["output"]) + \
               (cached_tokens / 1_000_000 * p["cached"])
    return cost

# --- Template Loading ---

def load_template(path: str, **kwargs) -> str:
    if not os.path.exists(path):
        return f"Template missing: {path}"
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    for key, val in kwargs.items():
        content = content.replace(f"{{{{{key}}}}}", str(val))
    return content

def get_accumulative_context(workspace: str, artifact_type: str) -> str:
    """Reads the current artifact from workspace to provide accumulative history."""
    path = os.path.join(workspace, f"{artifact_type}.md")
    if not os.path.exists(path): return ""
    
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    return f"\n<historical_feedback type=\"{artifact_type}\" mode=\"accumulative\">\n{content}\n</historical_feedback>\n"

# --- State & Config Management ---

def load_run_state(registry_path: str) -> Dict:
    state_path = os.path.join(registry_path, "run_state.json")
    if os.path.exists(state_path):
        with open(state_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "iteration": 0,
        "total_cost": 0.0,
        "total_api_requests": 0,
        "total_api_errors": 0,
        "api_error_manifest": {},
        "history": [],
        "status": "PENDING",
        "error": None
    }

def save_run_state(registry_path: str, state: Dict):
    os.makedirs(registry_path, exist_ok=True)
    state_path = os.path.join(registry_path, "run_state.json")
    with open(state_path, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

def update_stats(state: Dict, session: GeminiSession, model_id: str):
    s = session.stats
    input_tokens = s.get("inputTokens", 0)
    output_tokens = s.get("outputTokens", 0) + s.get("thoughtTokens", 0)
    cached_tokens = s.get("cachedTokens", 0)
    
    state["total_api_requests"] += s.get("totalRequests", 0)
    state["total_api_errors"] += s.get("totalErrors", 0)
    
    manifest = state.setdefault("api_error_manifest", {})
    for err in session.api_errors:
        key = f"Error {err.get('code')}: {err.get('message')}"
        manifest[key] = manifest.get(key, 0) + 1
    
    cost = calculate_cost(model_id, input_tokens, output_tokens, cached_tokens)
    state["total_cost"] += float(cost)

def get_project_context(workspace: str) -> str:
    context = []
    gemini_path = os.path.join(workspace, "GEMINI.md")
    if os.path.exists(gemini_path):
        with open(gemini_path, 'r', encoding='utf-8') as f:
            context.append(f"<project_context>\n{f.read()}\n</project_context>")
    
    designs_dir = os.path.join(workspace, "designs")
    if os.path.exists(designs_dir):
        design_files = [f for f in os.listdir(designs_dir) if f.endswith('.md')]
        if design_files:
            designs_context = ["<design_documents>"]
            for df in design_files:
                with open(os.path.join(designs_dir, df), 'r', encoding='utf-8') as f:
                    designs_context.append(f'<document path="designs/{df}">\n{f.read()}\n</document>')
            designs_context.append("</design_documents>")
            context.append("\n".join(designs_context))
            
    if not context: return ""
    return "\n<layer_3_context>\n" + "\n\n".join(context) + "\n</layer_3_context>\n"

from tools.validate_artifact import validate_artifact

DEFAULT_SCHEMAS_DIR = os.path.join(os.path.dirname(__file__), "schemas")

# --- Main Logic ---

def run_implementation(workspace: str, config: Dict):
    workspace = os.path.abspath(workspace)
    
    irq_path = os.path.join(workspace, "IRQ.md")
    qar_path = os.path.join(workspace, "QAR.md")
    
    if not os.path.exists(irq_path):
        print(f"ERROR: IRQ.md not found in {workspace}")
        return
    if not os.path.exists(qar_path):
        print(f"ERROR: QAR.md not found in {workspace}")
        return

    with open(irq_path, 'r', encoding='utf-8') as f:
        irq_content = f.read()
    with open(qar_path, 'r', encoding='utf-8') as f:
        qar_content = f.read()

    # 1. Setup Registry (Telemetry Only)
    run_id = config.get("run_id", f"run_{int(time.time())}")
    registry_path = os.path.join(config.get("registry_base", DEFAULT_REGISTRY_BASE), run_id)
    logs_dir = os.path.join(registry_path, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    with open(os.path.join(registry_path, "run_config.json"), 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)

    state = load_run_state(registry_path)
    if state["status"] in ["SUCCESS", "ABORTED", "DEADLOCK"]:
        print(f"Task already terminal: {state['status']}")
        return

    mem = config.get("memory_and_context", {})
    tmpl = config.get("templates_and_prompts", {})
    max_iters = config.get("max_iters", 3)
    model_doer = config.get("doer_model", "gemini-3-flash-preview")
    model_qa = config.get("qa_model", "gemini-3-flash-preview")

    project_context = get_project_context(workspace)

    for i in range(state["iteration"] + 1, max_iters + 1):
        state["iteration"] = i
        print(f"\n>>> ITERATION {i} <<<")

        # --- PHASE 1: DOER ---
        print(f"[DOER] Working (Model: {model_doer})...")
        
        doer_prompt = load_template(tmpl.get("doer_prompt_path", os.path.join(DEFAULT_TEMPLATES_DIR, "roles/doer_prompt.md")))
        irp_template = load_template(tmpl.get("irp_template_path", os.path.join(DEFAULT_TEMPLATES_DIR, "artifacts/irp_template.md")), round=i, last_qrp="QRP.md" if os.path.exists(os.path.join(workspace, "QRP.md")) else "None")
        
        # Accumulative Feedback from existing QRP/IRP
        history_context = get_accumulative_context(workspace, "QRP")
        history_context += get_accumulative_context(workspace, "IRP")
        
        full_prompt = f"{doer_prompt}\n\n<execution_artifacts>\n<IRQ>\n{irq_content}\n</IRQ>\n</execution_artifacts>\n\n"
        full_prompt += project_context
        full_prompt += f"\n\n<active_feedback>\n{history_context}\n</active_feedback>\n\n"
        full_prompt += f"<template id=\"irp\">\n{irp_template}\n</template>\n\nGo."

        session_id = None
        if mem.get("doer_amnesia_frequency", 1) != 1:
            session_id = f"{run_id}_doer_cont"

        irp_local = os.path.join(workspace, "IRP.md")
        for retry in range(2):
            session = run_gemini_cli_headless(full_prompt, model_id=model_doer, session_id=session_id, cwd=workspace)
            update_stats(state, session, model_doer)
            with open(os.path.join(logs_dir, f"v{i}_doer_try{retry+1}.log"), 'w', encoding='utf-8') as f:
                f.write(session.text)
            
            if os.path.exists(irp_local): break
            print(f"  [!] Missing IRP.md. Reprimanding...")
            full_prompt = f"ERROR: You did not create IRP.md. You MUST use your tools to write IRP.md to the workspace root.\n\n{full_prompt}"

        if os.path.exists(irp_local):
            git_commit(workspace, f"[DOER] Iteration {i}: Implementation")
        else:
            state["status"] = "ABORTED"
            state["error"] = "Doer failed to produce IRP.md"
            save_run_state(registry_path, state)
            break

        # --- PHASE 2: QA ---
        print(f"[QA] Auditing (Model: {model_qa})...")
        
        qa_prompt = load_template(tmpl.get("qa_prompt_path", os.path.join(DEFAULT_TEMPLATES_DIR, "roles/qa_prompt.md")))
        qrp_template = load_template(tmpl.get("qrp_template_path", os.path.join(DEFAULT_TEMPLATES_DIR, "artifacts/qrp_template.md")), round=i)
        
        # QA sees the current implementation report and accumulated history
        with open(irp_local, 'r', encoding='utf-8') as f:
            current_irp_content = f.read()
            
        full_prompt_qa = f"{qa_prompt}\n\n<execution_artifacts>\n<IRQ>\n{irq_content}\n</IRQ>\n<QAR>\n{qar_content}\n</QAR>\n</execution_artifacts>\n\n"
        full_prompt_qa += project_context
        full_prompt_qa += f"\n\n<historical_feedback>\n{get_accumulative_context(workspace, 'QRP')}\n</historical_feedback>\n\n"
        full_prompt_qa += f"<current_implementation>\n{current_irp_content}\n</current_implementation>\n\n"
        full_prompt_qa += f"<template id=\"qrp\">\n{qrp_template}\n</template>\n\nVerify."

        session_id_qa = None
        if mem.get("qa_amnesia_frequency", 1) != 1:
            session_id_qa = f"{run_id}_qa_cont"

        qrp_local = os.path.join(workspace, "QRP.md")
        qrp_schema = os.path.join(DEFAULT_SCHEMAS_DIR, "qrp_schema.json")
        for retry in range(2):
            session = run_gemini_cli_headless(full_prompt_qa, model_id=model_qa, session_id=session_id_qa, cwd=workspace)
            update_stats(state, session, model_qa)
            with open(os.path.join(logs_dir, f"v{i}_qa_try{retry+1}.log"), 'w', encoding='utf-8') as f:
                f.write(session.text)
            
            if os.path.exists(qrp_local):
                valid, errors = validate_artifact(qrp_local, qrp_schema)
                if valid: break
                else:
                    full_prompt_qa = f"ERROR: Your QRP.md failed validation:\n" + "\n".join([f"- {e}" for e in errors]) + f"\n\nPlease correct it.\n\n{full_prompt_qa}"
            else:
                full_prompt_qa = f"ERROR: You did not create QRP.md. You MUST use your tools to write QRP.md.\n\n{full_prompt_qa}"

        if os.path.exists(qrp_local):
            with open(qrp_local, 'r', encoding='utf-8') as f:
                content = f.read().lower()
                outcome = "to correct"
                if "outcome: final" in content: outcome = "final"
                elif "outcome: blocked" in content: outcome = "blocked"
            
            git_commit(workspace, f"[QA] Iteration {i}: {outcome.upper()}")
            state["history"].append({"iteration": i, "outcome": outcome})
            save_run_state(registry_path, state)

            if outcome == "final":
                print(f"SUCCESS: Approved at iteration {i}")
                state["status"] = "SUCCESS"
                break
            elif outcome == "blocked":
                print(f"BLOCKED at iteration {i}")
                state["status"] = "BLOCKED"
                break
        else:
            state["status"] = "ABORTED"
            state["error"] = "QA failed to produce QRP.md"
            save_run_state(registry_path, state)
            break

    if state["status"] == "PENDING":
        state["status"] = "FAILED"
    
    save_run_state(registry_path, state)
    print(f"\n--- RUN FINISHED: {state['status']} ---")
    print(f"Registry (Telemetry): {registry_path}")
    print(f"Total Cost: ${state['total_cost']:.4f}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--run-id", help="Explicit run ID for telemetry and branching")
    parser.add_argument("--config-file", help="Path to config JSON file")
    parser.add_argument("--doer-model", help="Override Doer model")
    parser.add_argument("--qa-model", help="Override QA model")
    parser.add_argument("--max-iters", type=int, help="Override max iterations")
    parser.add_argument("--registry-base", help="Override base directory for the central registry")
    parser.add_argument("--git-gate", action="store_true", help="Enable git gate")
    args = parser.parse_args()
    
    config = {
        "doer_model": "gemini-3-flash-preview",
        "qa_model": "gemini-3-flash-preview",
        "max_iters": 3,
        "run_id": args.run_id,
        "workspace": args.workspace,
        "memory_and_context": {
            "doer_amnesia_frequency": 1,
            "qa_amnesia_frequency": 1
        }
    }
    
    if args.config_file and os.path.exists(args.config_file):
        with open(args.config_file, 'r', encoding='utf-8') as f:
            config.update(json.load(f))
            
    if args.doer_model: config["doer_model"] = args.doer_model
    if args.qa_model: config["qa_model"] = args.qa_model
    if args.max_iters: config["max_iters"] = args.max_iters
    if args.registry_base: config["registry_base"] = args.registry_base
    if args.git_gate: config["git_gate"] = True

    run_implementation(args.workspace, config)

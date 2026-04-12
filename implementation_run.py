"""
Autonomous Implementation Orchestrator v2 (Central Registry & Amnesia)
"""

import os
import json
import shutil
import time
import hashlib
import argparse
import logging
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

def get_historical_context(registry_path: str, artifact_type: str, count: int) -> str:
    if count <= 0: return ""
    artifacts_dir = os.path.join(registry_path, "artifacts")
    if not os.path.exists(artifacts_dir): return ""
    
    files = sorted([f for f in os.listdir(artifacts_dir) if f'_{artifact_type}.md' in f], reverse=True)
    selected = files[:count]
    
    context = []
    for f in reversed(selected):
        round_num = f.split('_')[0].strip('v')
        with open(os.path.join(artifacts_dir, f), 'r', encoding='utf-8') as file:
            content = file.read()
        context.append(f'<{artifact_type} round="{round_num}">\n{content}\n</{artifact_type}>')
    
    if not context: return ""
    return f"\n<historical_feedback type=\"{artifact_type}\">\n" + "\n".join(context) + "\n</historical_feedback>\n"

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

# --- Main Logic ---

def run_implementation(workspace: str, config: Dict):
    workspace = os.path.abspath(workspace)
    irq_path = os.path.join(workspace, "IRQ.md")
    if not os.path.exists(irq_path):
        print(f"ERROR: IRQ.md not found in {workspace}")
        return

    # 1. Setup Registry
    run_id = config.get("run_id", f"run_{int(time.time())}")
    registry_path = os.path.join(config.get("registry_base", DEFAULT_REGISTRY_BASE), run_id)
    artifacts_dir = os.path.join(registry_path, "artifacts")
    logs_dir = os.path.join(registry_path, "logs")
    os.makedirs(artifacts_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)

    # 2. Save effective config
    with open(os.path.join(registry_path, "run_config.json"), 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)

    state = load_run_state(registry_path)
    if state["status"] in ["SUCCESS", "ABORTED", "DEADLOCK"]:
        print(f"Task already has terminal status: {state['status']}")
        return

    # Config params
    mem = config.get("memory_and_context", {})
    tmpl = config.get("templates_and_prompts", {})
    
    max_iters = config.get("max_iters", 3)
    model_doer = config.get("doer_model", "gemini-3-flash-preview")
    model_qa = config.get("qa_model", "gemini-3-flash-preview")

    for i in range(state["iteration"] + 1, max_iters + 1):
        state["iteration"] = i
        print(f"\n>>> ITERATION {i} <<<")

        # --- PHASE 1: DOER ---
        print(f"[DOER] Working (Model: {model_doer})...")
        
        # Build Context
        doer_prompt = load_template(tmpl.get("doer_prompt_path", os.path.join(DEFAULT_TEMPLATES_DIR, "roles/doer_prompt.md")))
        irp_template = load_template(tmpl.get("irp_template_path", os.path.join(DEFAULT_TEMPLATES_DIR, "artifacts/irp_template.md")), round=i, last_qrp=f"v{i-1}_QRP.md" if i > 1 else "None")
        
        history_qrp = get_historical_context(registry_path, "QRP", mem.get("doer_past_qrp_count", 1))
        history_irp = get_historical_context(registry_path, "IRP", mem.get("doer_past_irp_count", 0))
        
        full_prompt = f"{doer_prompt}\n\n<active_feedback>\n{history_qrp}\n{history_irp}\n</active_feedback>\n\n"
        full_prompt += f"<template id=\"irp\">\n{irp_template}\n</template>\n\nGo."

        # Session Amnesia
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
            print(f"  [!] Missing IRP.md. Reprimanding (Attempt {retry+1})...")
            full_prompt = f"ERROR: You did not create IRP.md. You MUST use your tools to write IRP.md to the workspace root.\n\n{full_prompt}"

        if os.path.exists(irp_local):
            irp_dest = os.path.join(artifacts_dir, f"v{i}_IRP.md")
            shutil.move(irp_local, irp_dest)
            print(f"  [+] Artifact moved to registry: v{i}_IRP.md")
        else:
            state["status"] = "ABORTED"
            state["error"] = "Doer failed to produce IRP.md"
            save_run_state(registry_path, state)
            break

        # --- PHASE 2: QA ---
        print(f"[QA] Auditing (Model: {model_qa})...")
        
        qa_prompt = load_template(tmpl.get("qa_prompt_path", os.path.join(DEFAULT_TEMPLATES_DIR, "roles/qa_prompt.md")))
        qrp_template = load_template(tmpl.get("qrp_template_path", os.path.join(DEFAULT_TEMPLATES_DIR, "artifacts/qrp_template.md")), round=i)
        
        # QA sees the latest IRP and history
        current_irp = get_historical_context(registry_path, "IRP", 1) # Always see current
        history_qrp_qa = get_historical_context(registry_path, "QRP", mem.get("qa_past_qrp_count", 2))
        
        full_prompt_qa = f"{qa_prompt}\n\n<historical_feedback>\n{history_qrp_qa}\n</historical_feedback>\n\n"
        full_prompt_qa += f"<current_implementation>\n{current_irp}\n</current_implementation>\n\n"
        full_prompt_qa += f"<template id=\"qrp\">\n{qrp_template}\n</template>\n\nVerify."

        session_id_qa = None
        if mem.get("qa_amnesia_frequency", 1) != 1:
            session_id_qa = f"{run_id}_qa_cont"

        qrp_local = os.path.join(workspace, "QRP.md")
        for retry in range(2):
            session = run_gemini_cli_headless(full_prompt_qa, model_id=model_qa, session_id=session_id_qa, cwd=workspace)
            update_stats(state, session, model_qa)
            with open(os.path.join(logs_dir, f"v{i}_qa_try{retry+1}.log"), 'w', encoding='utf-8') as f:
                f.write(session.text)
            
            if os.path.exists(qrp_local): break
            print(f"  [!] Missing QRP.md. Reprimanding (Attempt {retry+1})...")
            full_prompt_qa = f"ERROR: You did not create QRP.md. You MUST use your tools to write QRP.md to the workspace root.\n\n{full_prompt_qa}"

        if os.path.exists(qrp_local):
            qrp_dest = os.path.join(artifacts_dir, f"v{i}_QRP.md")
            shutil.move(qrp_local, qrp_dest)
            print(f"  [+] Artifact moved to registry: v{i}_QRP.md")
        else:
            state["status"] = "ABORTED"
            state["error"] = "QA failed to produce QRP.md"
            save_run_state(registry_path, state)
            break

        # Parse Outcome from registry file
        with open(qrp_dest, 'r', encoding='utf-8') as f:
            content = f.read()
            outcome = "to correct"
            if "outcome: final" in content.lower(): outcome = "final"
            elif "outcome: blocked" in content.lower(): outcome = "blocked"

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

    if state["status"] == "PENDING":
        state["status"] = "FAILED"
    
    save_run_state(registry_path, state)
    
    # Report
    print(f"\n--- RUN FINISHED: {state['status']} ---")
    print(f"Registry: {registry_path}")
    print(f"Total Cost: ${state['total_cost']:.4f}")
    print(f"API Requests: {state['total_api_requests']} (Errors: {state['total_api_errors']})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--config-file", help="Path to config JSON file")
    parser.add_argument("--doer-model", help="Override Doer model")
    parser.add_argument("--qa-model", help="Override QA model")
    parser.add_argument("--max-iters", type=int, help="Override max iterations")
    parser.add_argument("--registry-base", help="Override base directory for the central registry")
    args = parser.parse_args()
    
    config = {
        "doer_model": "gemini-3-flash-preview",
        "qa_model": "gemini-3-flash-preview",
        "max_iters": 3,
        "memory_and_context": {
            "doer_amnesia_frequency": 1,
            "qa_amnesia_frequency": 1,
            "doer_past_qrp_count": 1,
            "doer_past_irp_count": 0,
            "qa_past_qrp_count": 2,
            "qa_past_irp_count": 1
        }
    }
    
    if args.config_file and os.path.exists(args.config_file):
        with open(args.config_file, 'r', encoding='utf-8') as f:
            config.update(json.load(f))
            
    if args.doer_model: config["doer_model"] = args.doer_model
    if args.qa_model: config["qa_model"] = args.qa_model
    if args.max_iters: config["max_iters"] = args.max_iters
    if args.registry_base: config["registry_base"] = args.registry_base

    run_implementation(args.workspace, config)

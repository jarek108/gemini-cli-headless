"""
Standalone programmatic wrapper for the Gemini CLI in headless mode.
"""

import subprocess
import os
import json
import shutil
import logging
import re
import glob
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple

logger = logging.getLogger("gemini_cli_headless")

@dataclass
class GeminiSession:
    """
    Represents a completed Gemini CLI session interaction.
    """
    text: str
    session_id: str
    session_path: str
    stats: Dict[str, Any] = field(default_factory=dict)
    api_errors: List[Dict[str, Any]] = field(default_factory=list)
    raw_data: Dict[str, Any] = field(default_factory=dict)

def _get_cli_chat_dir(project_name: str) -> str:
    """Returns the internal Gemini CLI chat directory for a given project."""
    return os.path.join(os.path.expanduser("~"), ".gemini", "tmp", project_name, "chats")

def _sanitize_project_name(name: str) -> str:
    """Sanitizes a string to match the Gemini CLI project name convention."""
    sanitized = re.sub(r'[^a-z0-9]+', '-', name.lower())
    return sanitized.strip('-')

def _find_session_file(directory: str, session_id: str) -> Optional[str]:
    """Locates a session file matching the ID prefix in the given directory."""
    if not os.path.exists(directory):
        return None
    short_id = session_id[:8]
    patterns = [f"session-*{short_id}*.json", f"*{short_id}*.json"]
    for pattern in patterns:
        matches = glob.glob(os.path.join(directory, pattern))
        if matches:
            return sorted(matches, key=os.path.getmtime, reverse=True)[0]
    return None

def run_gemini_cli_headless(
    prompt: str,
    model_id: Optional[str] = None,
    files: Optional[List[str]] = None,
    session_id: Optional[str] = None,
    session_to_resume: Optional[str] = None,
    project_name: Optional[str] = None,
    cwd: Optional[str] = None,
    extra_args: Optional[List[str]] = None
) -> GeminiSession:
    """
    Standalone wrapper for the Gemini CLI in headless mode.
    """
    if not project_name:
        base_dir = cwd if cwd else os.getcwd()
        project_name = _sanitize_project_name(os.path.basename(base_dir))

    session_id_to_use = session_id
    cli_dir = _get_cli_chat_dir(project_name)
    
    if session_to_resume:
        if session_to_resume.lower().endswith('.json') or os.path.isfile(session_to_resume):
            if not os.path.exists(session_to_resume):
                raise FileNotFoundError(f"Session file not found: {session_to_resume}")
            with open(session_to_resume, 'r', encoding='utf-8') as f:
                data = json.load(f)
                session_id_to_use = data.get("sessionId")
            if not session_id_to_use:
                raise ValueError(f"File {session_to_resume} is not a valid Gemini session")
            if session_id_to_use.startswith('init-'):
                session_id_to_use = None
            else:
                os.makedirs(cli_dir, exist_ok=True)
                target_path = os.path.join(cli_dir, f"session-{session_id_to_use}.json")
                shutil.copy2(session_to_resume, target_path)
        else:
            session_id_to_use = session_to_resume

    # Construct prompt string with attachments
    full_prompt = prompt
    if files:
        for f_path in files:
            if os.path.exists(f_path):
                full_prompt += f" @{os.path.abspath(f_path)}"

    # Build command
    cmd_executable = "gemini.cmd" if os.name == 'nt' else "gemini"
    cmd = [cmd_executable, "-y", "-o", "json"]
    if model_id: cmd.extend(["-m", model_id])
    if session_id_to_use: cmd.extend(["-r", session_id_to_use])
    if extra_args: cmd.extend(extra_args)
    
    # Execute by piping the prompt to stdin
    result = subprocess.run(
        cmd, 
        cwd=cwd, 
        capture_output=True, 
        text=True, 
        encoding='utf-8', 
        check=False,
        input=full_prompt
    )

    combined_output = (result.stdout or "") + (result.stderr or "")
    
    if not combined_output.strip():
        raise RuntimeError(f"CLI returned absolutely empty output.")

    # Find all JSON-looking blocks and try to parse them from the end
    # (The actual response is usually the last valid JSON object)
    
    response_data = None
    last_error = None
    
    # Search for valid JSON from the end of the output
    search_pos = len(combined_output)
    while search_pos > 0:
        start_idx = combined_output.rfind('{', 0, search_pos)
        if start_idx == -1:
            break
            
        # Try to find a matching closing brace
        brace_count = 0
        end_idx = -1
        for i in range(start_idx, len(combined_output)):
            if combined_output[i] == '{':
                brace_count += 1
            elif combined_output[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i
                    break
        
        if end_idx != -1:
            json_str = combined_output[start_idx:end_idx+1]
            try:
                candidate = json.loads(json_str)
                # We want a block that looks like a Gemini response (has session_id or response or error)
                if isinstance(candidate, dict) and ("session_id" in candidate or "response" in candidate or "text" in candidate or "error" in candidate):
                    response_data = candidate
                    break
            except json.JSONDecodeError as e:
                last_error = e
        
        search_pos = start_idx

    if not response_data:
        raise RuntimeError(f"CLI output did not contain a valid Gemini response JSON. Last error: {last_error}\nOutput: {combined_output[:500]}...")
    
    # 1. Capture errors from logs (retries)
    # Pattern: "failed with status 503"
    api_errors = []
    retry_matches = re.findall(r"failed with status (\d+)", combined_output)
    for code in retry_matches:
        api_errors.append({"code": int(code), "message": "Transient API Error (Retry)"})

    # 2. Check for terminal error in JSON
    if "error" in response_data and response_data["error"]:
        err = response_data["error"]
        msg = err.get("message") if isinstance(err, dict) else str(err)
        code = err.get("code", "unknown") if isinstance(err, dict) else "unknown"
        api_errors.append({"code": code, "message": msg})
        # If it's a terminal error and we have no response text, we should probably raise
        if not response_data.get("response") and not response_data.get("text"):
            raise RuntimeError(f"Gemini Error: {msg} (Code: {code})")

    final_session_id = response_data.get("session_id") or session_id_to_use
    final_session_path = _find_session_file(cli_dir, final_session_id)
    if not final_session_path:
        tmp_root = os.path.join(os.path.expanduser("~"), ".gemini", "tmp")
        if os.path.exists(tmp_root):
            for p_dir in os.listdir(tmp_root):
                candidate = _find_session_file(os.path.join(tmp_root, p_dir, "chats"), final_session_id)
                if candidate:
                    final_session_path = candidate
                    break
        if not final_session_path:
            final_session_path = os.path.join(cli_dir, f"session-{final_session_id}.json")

    # Extract and aggregate stats from the root 'stats' object
    stats_raw = response_data.get("stats", {})
    aggregated_stats = {
        "inputTokens": 0,
        "outputTokens": 0,
        "thoughtTokens": 0,
        "cachedTokens": 0,
        "totalRequests": 0,
        "totalErrors": 0
    }
    
    if "models" in stats_raw:
        for model_data in stats_raw["models"].values():
            tokens = model_data.get("tokens", {})
            aggregated_stats["inputTokens"] += tokens.get("input", 0)
            aggregated_stats["outputTokens"] += tokens.get("candidates", 0)
            aggregated_stats["thoughtTokens"] += tokens.get("thoughts", 0)
            aggregated_stats["cachedTokens"] += tokens.get("cached", 0)
            
            api = model_data.get("api", {})
            aggregated_stats["totalRequests"] += api.get("totalRequests", 0)
            aggregated_stats["totalErrors"] += api.get("totalErrors", 0)
    
    return GeminiSession(
        text=response_data.get("text", "") or response_data.get("response", ""),
        session_id=final_session_id,
        session_path=final_session_path,
        stats=aggregated_stats,
        api_errors=api_errors,
        raw_data=response_data
    )

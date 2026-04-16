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
import time
import tempfile
import threading
import sys
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

DEFAULT_ALLOWED_TOOLS = [
    "read_file",
    "list_directory",
    "grep_search",
    "glob"
]

def _find_session_file(directory: str, session_id: str) -> str:
    """Locates a session file matching the ID prefix. Retries with small delay."""
    if not os.path.exists(directory):
        return os.path.join(directory, f"session-{session_id}.json")
    
    short_id = session_id[:8]
    patterns = [f"session-*{short_id}*.json", f"*{short_id}*.json"]
    
    for attempt in range(5):
        for pattern in patterns:
            matches = glob.glob(os.path.join(directory, pattern))
            if matches:
                return sorted(matches, key=os.path.getmtime, reverse=True)[0]
        time.sleep(0.5)
        
    return os.path.join(directory, f"session-{session_id}.json")

def _sanitize_project_name(name: str) -> str:
    """Sanitizes a string to match the Gemini CLI project name convention."""
    sanitized = re.sub(r'[^a-z0-9]+', '-', name.lower())
    return sanitized.strip('-')

def _get_cli_chat_dir(project_name: str) -> str:
    """Returns the internal Gemini CLI chat directory for a given project."""
    return os.path.join(os.path.expanduser("~"), ".gemini", "tmp", project_name, "chats")

def run_gemini_cli_headless(
    prompt: str,
    model_id: Optional[str] = None,
    files: Optional[List[str]] = None,
    session_id: Optional[str] = None,
    session_to_resume: Optional[str] = None,
    project_name: Optional[str] = None,
    cwd: Optional[str] = None,
    extra_args: Optional[List[str]] = None,
    stream_output: bool = False,
    # --- Resilience & Auth Params ---
    api_key: Optional[str] = None,
    max_retries: int = 3,
    retry_delay_seconds: float = 5.0,
    # --- Security & Scope Controls ---
    allowed_tools: Optional[List[str]] = None,
    allowed_paths: Optional[List[str]] = None
) -> GeminiSession:
    """
    Standalone wrapper for the Gemini CLI in headless mode.
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return _execute_single_run(
                prompt=prompt,
                model_id=model_id,
                files=files,
                session_id=session_id,
                session_to_resume=session_to_resume,
                project_name=project_name,
                cwd=cwd,
                extra_args=extra_args,
                stream_output=stream_output,
                api_key=api_key,
                allowed_tools=allowed_tools,
                allowed_paths=allowed_paths
            )
        except (RuntimeError, json.JSONDecodeError) as e:
            last_exception = e
            if attempt < max_retries - 1:
                logger.warning(f"Gemini CLI failed (Attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay_seconds}s... Error: {e}")
                time.sleep(retry_delay_seconds)
            else:
                logger.error(f"Gemini CLI failed all {max_retries} attempts.")
                raise last_exception

def _execute_single_run(
    prompt: str,
    model_id: Optional[str] = None,
    files: Optional[List[str]] = None,
    session_id: Optional[str] = None,
    session_to_resume: Optional[str] = None,
    project_name: Optional[str] = None,
    cwd: Optional[str] = None,
    extra_args: Optional[List[str]] = None,
    stream_output: bool = False,
    api_key: Optional[str] = None,
    allowed_tools: Optional[List[str]] = None,
    allowed_paths: Optional[List[str]] = None
) -> GeminiSession:
    """Internal execution logic for a single CLI invocation."""
    
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
            
            os.makedirs(cli_dir, exist_ok=True)
            target_path = os.path.join(cli_dir, f"session-{session_id_to_use}.json")
            shutil.copy2(session_to_resume, target_path)
        else:
            session_id_to_use = session_to_resume

    attachment_strings = []
    if files:
        for f_path in files:
            if os.path.exists(f_path):
                attachment_strings.append(f" @{os.path.abspath(f_path)}")

    cmd_executable = shutil.which("gemini")
    if not cmd_executable:
        raise EnvironmentError("The 'gemini' executable was not found in your PATH.")

    cmd = [cmd_executable, "--yolo", "-o", "json"]
    if model_id: cmd.extend(["-m", model_id])
    if session_id_to_use: cmd.extend(["-r", session_id_to_use])
    if extra_args: cmd.extend(extra_args)

    policy_path = None
    prompt_path = None
    
    try:
        temp_dir = os.path.join(os.path.expanduser("~"), ".gemini", "tmp", project_name, "run")
        os.makedirs(temp_dir, exist_ok=True)

        tools_whitelist = allowed_tools if allowed_tools is not None else DEFAULT_ALLOWED_TOOLS
        paths_whitelist = allowed_paths if allowed_paths is not None else [cwd if cwd else os.getcwd()]
        if temp_dir not in paths_whitelist and "*" not in paths_whitelist:
            paths_whitelist.append(temp_dir)
            
        policy_lines = []
        if tools_whitelist != ["*"]:
            policy_lines.append("tools:")
            policy_lines.append("  - name: \"*\"")
            policy_lines.append("    action: deny")
            for tool in tools_whitelist:
                policy_lines.append(f"  - name: \"{tool}\"")
                policy_lines.append("    action: allow")
            
        if paths_whitelist != ["*"]:
            policy_lines.append("fileSystem:")
            policy_lines.append("  allowedPaths:")
            for p in paths_whitelist:
                abs_p = os.path.abspath(p).replace('\\', '/')
                policy_lines.append(f"    - \"{abs_p}\"")
            
        if policy_lines:
            with tempfile.NamedTemporaryFile(mode='w', suffix=".yaml", dir=temp_dir, delete=False, encoding='utf-8') as tf:
                tf.write("\n".join(policy_lines))
                policy_path = tf.name
            cmd.extend(["--policy", policy_path])

        with tempfile.NamedTemporaryFile(mode='w', suffix=".txt", dir=temp_dir, delete=False, encoding='utf-8') as tf:
            tf.write(prompt)
            for att in attachment_strings:
                tf.write(att)
            prompt_path = tf.name
        cmd.append(f"@{prompt_path}")

        env = os.environ.copy()
        env["TERM"] = "dumb"
        env["NO_COLOR"] = "1"
        if api_key:
            env["GEMINI_API_KEY"] = api_key

        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            bufsize=1
        )

        combined_output_list = []
        
        # Thread function to read output and print in real-time
        def read_output():
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                combined_output_list.append(line)
                if stream_output:
                    sys.stdout.write(line)
                    sys.stdout.flush()

        output_thread = threading.Thread(target=read_output)
        output_thread.start()

        # Main loop: Heartbeat to prevent environment timeout
        while output_thread.is_alive():
            if not stream_output:
                # Print a small dot as heartbeat if we're not already streaming
                sys.stdout.write(".")
                sys.stdout.flush()
            output_thread.join(timeout=30)
            
        process.wait()
        combined_output = "".join(combined_output_list)

        start_idx = combined_output.find('{')
        end_idx = combined_output.rfind('}')
        if start_idx == -1 or end_idx == -1:
            raise RuntimeError(f"CLI did not return JSON. Output: {combined_output}")
        
        data = json.loads(combined_output[start_idx:end_idx+1])
        
        return GeminiSession(
            text=data.get("text", ""),
            session_id=data.get("session_id") or session_id_to_use,
            session_path=_find_session_file(cli_dir, data.get('session_id') or session_id_to_use or ""),
            stats=data.get("trace", {}).get("stats", {}),
            raw_data=data
        )

    finally:
        if policy_path and os.path.exists(policy_path):
            try: os.remove(policy_path)
            except: pass
        if prompt_path and os.path.exists(prompt_path):
            try: os.remove(prompt_path)
            except: pass

import os
import sys
import subprocess
import json
import time
import shutil
import tempfile
import threading
import re
import glob
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Union

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("gemini-cli-headless")

@dataclass
class GeminiSession:
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

def _find_project_root(start_dir: str) -> str:
    """Climbs upwards to find the nearest workspace root (.gemini, .git, or .project_root)."""
    current = os.path.abspath(start_dir)
    while True:
        if os.path.exists(os.path.join(current, ".gemini")) or \
           os.path.exists(os.path.join(current, ".git")) or \
           os.path.exists(os.path.join(current, ".project_root")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return start_dir

def _get_gemini_tmp_root(gemini_home: Optional[str] = None) -> str:
    """Returns the root temporary directory for Gemini sessions, respecting GEMINI_CLI_HOME."""
    if not gemini_home:
        gemini_home = os.environ.get("GEMINI_CLI_HOME")
    if not gemini_home:
        if os.name == "nt":
            gemini_home = os.environ.get("USERPROFILE", os.path.expanduser("~"))
        else:
            gemini_home = os.path.expanduser("~")
    
    return os.path.join(gemini_home, ".gemini", "tmp")

def _find_session_file(directory: str, session_id: str, tmp_root: Optional[str] = None) -> str:
    """
    Locates a session file matching the ID prefix. 
    If not found in the primary directory, searches all projects in tmp_root.
    """
    short_id = session_id[:8]
    patterns = [f"session-*{short_id}*.json", f"*{short_id}*.json"]
    
    # Try primary directory first
    if os.path.exists(directory):
        for attempt in range(3):
            for pattern in patterns:
                matches = glob.glob(os.path.join(directory, pattern))
                if matches:
                    return sorted(matches, key=os.path.getmtime, reverse=True)[0]
            time.sleep(0.5)

    # Fallback: search globally in tmp_root across all project folders
    if tmp_root and os.path.exists(tmp_root):
        global_patterns = [
            os.path.join("*", "chats", f"session-*{short_id}*.json"),
            os.path.join("*", "chats", f"*{short_id}*.json")
        ]
        for attempt in range(5):
            for gp in global_patterns:
                matches = glob.glob(os.path.join(tmp_root, gp))
                if matches:
                    return sorted(matches, key=os.path.getmtime, reverse=True)[0]
            time.sleep(0.5)
        
    return os.path.join(directory, f"session-{session_id}.json")

def _sanitize_project_name(name: str) -> str:
    """Sanitizes a string to match the Gemini CLI project name convention (slugify)."""
    sanitized = re.sub(r'[^a-z0-9]+', '-', name.lower())
    return sanitized.strip('-') or 'project'

def _get_cli_chat_dir(project_name: str, tmp_root: str) -> str:
    """Returns the internal Gemini CLI chat directory for a given project."""
    return os.path.join(tmp_root, project_name, "chats")

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
    timeout_seconds: Optional[int] = 300, 
    # --- Security & Scope Controls ---
    allowed_tools: Optional[List[str]] = None,
    allowed_paths: Optional[List[str]] = None,
    allowed_commands: Optional[List[str]] = None,
    system_instruction_override: Optional[str] = None,
    isolate_from_hierarchical_pollution: bool = True
) -> GeminiSession:
    """
    Standalone wrapper for the Gemini CLI in headless mode.
    """
    
    # Python-level path security for attachments
    if allowed_paths is not None and allowed_paths != ["*"]:
        base_dir = cwd if cwd else os.getcwd()
        resolved_whitelist = []
        for p in allowed_paths:
            if not os.path.isabs(p):
                resolved_whitelist.append(os.path.abspath(os.path.join(base_dir, p)).lower())
            else:
                resolved_whitelist.append(os.path.abspath(p).lower())
        
        if files:
            for f_path in files:
                abs_f = os.path.abspath(f_path).lower()
                is_safe = False
                for allowed in resolved_whitelist:
                    if abs_f.startswith(allowed):
                        is_safe = True
                        break
                if not is_safe:
                    raise PermissionError(f"Access to file '{f_path}' is not allowed by the security policy.")

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
                allowed_paths=allowed_paths,
                allowed_commands=allowed_commands,
                timeout_seconds=timeout_seconds,
                system_instruction_override=system_instruction_override,
                isolate_from_hierarchical_pollution=isolate_from_hierarchical_pollution
            )
        except (RuntimeError, json.JSONDecodeError, PermissionError) as e:
            last_exception = e
            if "exhausted" in str(e).lower() or "quota" in str(e).lower() or "429" in str(e):
                logger.error(f"Gemini API Quota Exhausted (429). Failing fast.")
                raise last_exception
            
            if isinstance(e, PermissionError):
                raise last_exception

            if attempt < max_retries - 1:
                logger.warning(f"Gemini CLI failed (Attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay_seconds}s... Error: {e}")
                time.sleep(retry_delay_seconds)
            else:
                logger.error(f"Gemini CLI failed all {max_retries} attempts.")
                raise last_exception
        except subprocess.TimeoutExpired:
            logger.error(f"Gemini CLI timed out after {timeout_seconds}s.")
            raise

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
    allowed_paths: Optional[List[str]] = None,
    allowed_commands: Optional[List[str]] = None,
    timeout_seconds: Optional[int] = 300,
    system_instruction_override: Optional[str] = None,
    isolate_from_hierarchical_pollution: bool = True
) -> GeminiSession:
    """Internal execution logic for a single CLI invocation."""
    
    effective_cwd = cwd if cwd else os.getcwd()
    
    # 1. PROJECT NAME & ROOT RESOLUTION
    # We resolve the root to ensure we use the 'workspace' name if possible.
    resolved_root = _find_project_root(effective_cwd)
    if not project_name:
        project_name = _sanitize_project_name(os.path.basename(resolved_root))

    # 2. SURGICAL ISOLATION (GEMINI_CLI_HOME trick)
    # The only 100% reliable way to stop the CLI from crawling up for context is to 
    # trigger the isHomeDirectory check by setting GEMINI_CLI_HOME to the CWD.
    gemini_home_override = effective_cwd if isolate_from_hierarchical_pollution else None
    tmp_root = _get_gemini_tmp_root(gemini_home_override)

    session_id_to_use = session_id
    cli_dir = _get_cli_chat_dir(project_name, tmp_root)

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
            session_id_to_use = session_id_to_resume

    attachment_strings = []
    if files:
        for f_path in files:
            if os.path.exists(f_path):
                attachment_strings.append(f" @{os.path.abspath(f_path)}")

    cmd_executable = shutil.which("gemini")
    if not cmd_executable:
        raise EnvironmentError("The 'gemini' executable was not found in your PATH.")

    cmd = [cmd_executable, "-o", "json"]
    if model_id: cmd.extend(["-m", model_id])
    if session_id_to_use: cmd.extend(["-r", session_id_to_use])
    if extra_args: cmd.extend(extra_args)

    policy_path = None
    prompt_path = None
    system_md_path = None
    
    env = os.environ.copy()
    env["TERM"] = "dumb"
    env["NO_COLOR"] = "1"
    env["CI"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    if api_key:
        env["GEMINI_API_KEY"] = api_key
    elif not env.get("GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY is missing. You must set it in your environment or pass it via the 'api_key' argument.")

    try:
        # Apply isolation via GEMINI_CLI_HOME
        if isolate_from_hierarchical_pollution:
            env["GEMINI_CLI_HOME"] = effective_cwd

        if effective_cwd and os.path.exists(effective_cwd):
            temp_dir = os.path.join(effective_cwd, ".gemini_headless")
        else:
            temp_dir = os.path.join(tmp_root, project_name, "run")
        
        os.makedirs(temp_dir, exist_ok=True)

        # Persona Control (GEMINI_SYSTEM_MD override)
        if system_instruction_override:
            with tempfile.NamedTemporaryFile(mode='w', suffix=".md", dir=temp_dir, delete=False, encoding='utf-8') as tf:
                tf.write(system_instruction_override)
                system_md_path = tf.name
            env["GEMINI_SYSTEM_MD"] = system_md_path

        tools_whitelist = allowed_tools if allowed_tools is not None else DEFAULT_ALLOWED_TOOLS
        paths_whitelist = allowed_paths if allowed_paths is not None else ["*"]
        commands_whitelist = allowed_commands if allowed_commands is not None else []

        policy_lines = []
        PRIO_RESTRICTED_ALLOW = 999 
        PRIO_GENERAL_DENY = 900
        PRIO_GENERAL_ALLOW = 500
        PRIO_CATCHALL = 0

        # Dangerous tools list
        path_sensitive_tools = ["read_file", "write_file", "list_directory", "grep_search", "glob", "replace"]
        un_sandboxable_tools = ["run_shell_command", "web_fetch"]
        restricted_tools = path_sensitive_tools + un_sandboxable_tools

        # 1. PATH SECURITY & TOOL WHITELISTING (Tier 5 Structural)
        if paths_whitelist != ["*"]:
            policy_lines.append("[policy.restricted_paths]")
            policy_lines.append(f"paths = {json.dumps(paths_whitelist)}")
            policy_lines.append(f"priority = {PRIO_RESTRICTED_ALLOW}")
            policy_lines.append("decision = \"ALLOW\"")
            policy_lines.append("tools = [\"*\"]\n")
            
            policy_lines.append("[policy.deny_all_path_sensitive]")
            policy_lines.append(f"tools = {json.dumps(path_sensitive_tools)}")
            policy_lines.append(f"priority = {PRIO_GENERAL_DENY}")
            policy_lines.append("decision = \"DENY\"\n")

        # 2. SHELL COMMAND WHITELISTING (Native)
        if "run_shell_command" in tools_whitelist or tools_whitelist == ["*"]:
            if commands_whitelist:
                # Surgical prefix allow
                for idx, cmd_prefix in enumerate(commands_whitelist):
                    policy_lines.append(f"[policy.allow_command_{idx}]")
                    policy_lines.append(f"tools = [\"run_shell_command\"]")
                    policy_lines.append(f"priority = {PRIO_RESTRICTED_ALLOW}")
                    policy_lines.append("decision = \"ALLOW\"")
                    # Use regex to match start of command
                    safe_prefix = re.escape(cmd_prefix)
                    policy_lines.append(f"parameters = {{ command = {{ regex = \"^{safe_prefix}\" }} }}\n")
                
                # Deny all other shell commands
                policy_lines.append("[policy.deny_other_shell]")
                policy_lines.append("tools = [\"run_shell_command\"]")
                policy_lines.append(f"priority = {PRIO_GENERAL_DENY}")
                policy_lines.append("decision = \"DENY\"\n")
        else:
            # Deny run_shell_command entirely
            policy_lines.append("[policy.deny_shell_entirely]")
            policy_lines.append("tools = [\"run_shell_command\"]")
            policy_lines.append(f"priority = {PRIO_GENERAL_DENY}")
            policy_lines.append("decision = \"DENY\"\n")

        # 3. GENERAL TOOL WHITELISTING
        if tools_whitelist != ["*"]:
            policy_lines.append("[policy.allow_whitelisted_tools]")
            policy_lines.append(f"tools = {json.dumps(tools_whitelist)}")
            policy_lines.append(f"priority = {PRIO_GENERAL_ALLOW}")
            policy_lines.append("decision = \"ALLOW\"\n")
            
            policy_lines.append("[policy.deny_unlisted_tools]")
            policy_lines.append("tools = [\"*\"]")
            policy_lines.append(f"priority = {PRIO_CATCHALL}")
            policy_lines.append("decision = \"DENY\"\n")
        else:
            policy_lines.append("[policy.allow_all_tools]")
            policy_lines.append("tools = [\"*\"]")
            policy_lines.append(f"priority = {PRIO_GENERAL_ALLOW}")
            policy_lines.append("decision = \"ALLOW\"\n")

        # Write policy file
        with tempfile.NamedTemporaryFile(mode='w', suffix=".toml", dir=temp_dir, delete=False, encoding='utf-8') as tf:
            tf.write("\n".join(policy_lines))
            policy_path = tf.name
        cmd.extend(["--policy", policy_path])

        # Contract Enforcement (In-Prompt)
        contract_prefix = ""
        if tools_whitelist != ["*"]:
            contract_prefix += f"\n[CONTRACT] You are in a restricted headless environment. Allowed tools: {', '.join(tools_whitelist)}.\n"
        if paths_whitelist != ["*"]:
             contract_prefix += f"[CONTRACT] File access is restricted to: {', '.join(paths_whitelist)}.\n"
        
        full_prompt = contract_prefix + prompt + "".join(attachment_strings)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=".txt", dir=temp_dir, delete=False, encoding='utf-8') as tf:
            tf.write(full_prompt)
            prompt_path = tf.name
        cmd.append(f"@{prompt_path}")

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

        while output_thread.is_alive():
            if not stream_output:
                sys.stdout.write(".")
                sys.stdout.flush()
            output_thread.join(timeout=30)
            
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            raise
            
        combined_output = "".join(combined_output_list)

        lowered_output = combined_output.lower()
        if "exhausted" in lowered_output or "quota" in lowered_output or "429" in lowered_output:
             is_terminal = "daily limit" in lowered_output or "capacity" in lowered_output
             error_kind = "Daily Quota Exhausted (Terminal)" if is_terminal else "Rate Limit Exceeded (Retryable)"
             raise RuntimeError(f"Gemini API {error_kind}. Output: {combined_output[:500]}")
        
        if ("modelnotfounderror" in lowered_output or "model not found" in lowered_output) and "error executing tool" not in lowered_output:
             raise RuntimeError(f"Gemini Model Not Found.")

        data = None
        for match in re.finditer(r'\{', combined_output):
            start_idx = match.start()
            for end_match in re.finditer(r'\}', combined_output[start_idx:]):
                end_idx = start_idx + end_match.start() + 1
                try:
                    candidate = json.loads(combined_output[start_idx:end_idx])
                    if "session_id" in candidate or "text" in candidate or "error" in candidate:
                        data = candidate
                except json.JSONDecodeError:
                    continue
        
        if not data:
            raise RuntimeError(f"CLI did not return valid JSON session data. Output: {combined_output}")

        if "error" in data:
            err_msg = data["error"].get("message", "Unknown error")
            raise RuntimeError(f"Gemini CLI Error: {err_msg}")
        
        text_content = data.get("text") or data.get("response") or ""
        stats_content = data.get("stats") or data.get("trace", {}).get("stats", {})

        if "tools" in stats_content and isinstance(stats_content["tools"], dict):
             stats_content["totalCalls"] = stats_content["tools"].get("totalCalls", 0)
             stats_content["totalSuccess"] = stats_content["tools"].get("totalSuccess", 0)

        final_session_id = data.get("session_id") or session_id_to_use or ""
        
        return GeminiSession(
            text=text_content,
            session_id=final_session_id,
            session_path=_find_session_file(cli_dir, final_session_id, tmp_root),
            stats=stats_content,
            raw_data=data
        )

    finally:
        if policy_path and os.path.exists(policy_path):
            try: os.remove(policy_path)
            except: pass
        if prompt_path and os.path.exists(prompt_path):
            try: os.remove(prompt_path)
            except: pass
        if system_md_path and os.path.exists(system_md_path):
            try: os.remove(system_md_path)
            except: pass

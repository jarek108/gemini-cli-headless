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

class QuotaExhaustedError(RuntimeError):
    """Base class for quota errors."""
    pass

class MinuteQuotaExhaustedError(QuotaExhaustedError):
    """Raised when the per-minute rate limit is reached."""
    pass

class DailyQuotaExhaustedError(QuotaExhaustedError):
    """Raised when the daily quota is reached."""
    pass

def _is_quota_error(text: str) -> bool:
    """Uses precise regex to detect quota-related errors, avoiding false positives like '429' in IDs."""
    if not text:
        return False
    
    patterns = [
        r'(?i)quota\s+exhausted',
        r'(?i)rate\s+limit\s+reached',
        r'(?i)too\s+many\s+requests',
        r'(?i)status[:\s]+429',
        r'(?i)"code"[:\s]+429',
        r'(?i)429\s+too\s+many\s+requests'
    ]
    for pattern in patterns:
        if re.search(pattern, text):
            return True
    return False

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

def _resolve_real_home_dir() -> str:
    """Returns the real user home directory, bypassing GEMINI_CLI_HOME entirely.

    On Windows, prefers USERPROFILE but falls through to os.path.expanduser
    if it is missing OR empty (the `or` guard matters — an empty USERPROFILE
    would otherwise produce a bogus `/.gemini/tmp` path).
    """
    if os.name == "nt":
        return os.environ.get("USERPROFILE") or os.path.expanduser("~")
    return os.path.expanduser("~")

def _get_gemini_tmp_root(gemini_home: Optional[str] = None) -> str:
    """Returns the root temporary directory for Gemini sessions, respecting GEMINI_CLI_HOME."""
    if not gemini_home:
        gemini_home = os.environ.get("GEMINI_CLI_HOME")
    if not gemini_home:
        gemini_home = _resolve_real_home_dir()

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

def _wait_for_session_flush(session_path: str, expected_messages_count: int, timeout: float = 10.0):
    """
    Waits for the session file on disk to be updated with the expected number of messages.
    Ensures atomicity between CLI output and file state.
    """
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(session_path):
            try:
                with open(session_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    messages = data.get("messages", [])
                    if len(messages) >= expected_messages_count:
                        return True
            except (json.JSONDecodeError, IOError):
                pass
        time.sleep(0.5)
    return False

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
    auth_mode: str = "api_key",
    max_retries: int = 3,
    retry_delay_seconds: float = 5.0,
    timeout_seconds: Optional[int] = 300,
    # --- Security & Scope Controls ---
    allowed_tools: Optional[List[str]] = None,
    allowed_paths: Optional[List[str]] = None,
    allowed_commands: Optional[List[str]] = None,
    system_instruction_override: Optional[str] = None,
    isolate_from_hierarchical_pollution: bool = True,
    inject_enforcement_contract: bool = True,
    force_fresh: bool = False
) -> GeminiSession:
    """
    Standalone wrapper for the Gemini CLI in headless mode.
    Secured via Tier-4 Sandboxing logic.

    Auth:
        auth_mode: How the subprocess authenticates with Gemini.
            - "api_key" (default): the wrapper requires
              `GEMINI_API_KEY` either in the environment or via the `api_key`
              kwarg, and raises `ValueError` otherwise. When
              `isolate_from_hierarchical_pollution=True` the subprocess gets
              `GEMINI_CLI_HOME=<cwd>` for clean-room isolation.
            - "oauth": the wrapper does NOT require or set `GEMINI_API_KEY`;
              it strips any inherited `GEMINI_API_KEY` and `GEMINI_CLI_HOME`
              from the subprocess so the CLI resolves OAuth credentials from
              the real home (`~/.gemini/oauth_creds.json`, as produced by
              `gemini auth login`). The rest of the isolation (project tmp
              dir, `GEMINI_PROJECT`, and `GEMINI_SYSTEM_MD` when
              `system_instruction_override` is provided) still applies.
            Any other value raises `ValueError`. Passing `auth_mode="oauth"`
            together with `api_key=...` is a conflict and also raises
            `ValueError` (no silent drop).
    """

    # Validate auth_mode up-front so bad values fail fast before any retries.
    if auth_mode not in ("api_key", "oauth"):
        raise ValueError(
            f"Invalid auth_mode={auth_mode!r}. Expected 'api_key' or 'oauth'."
        )
    if auth_mode == "oauth" and api_key:
        raise ValueError(
            "auth_mode='oauth' is incompatible with api_key=... "
            "Pick one: either pass api_key (and leave auth_mode='api_key') "
            "or use OAuth creds from `gemini auth login` (auth_mode='oauth')."
        )

    # Python-level path security for attachments
    if allowed_paths is not None and allowed_paths != ["*"]:
        logger.warning(
            "\n🚨 CRITICAL WARNING: PATH SECURITY IS BROKEN UPSTREAM 🚨\n"
            "You have provided 'allowed_paths'. Due to a static compiler bug in the upstream "
            "Gemini CLI policy engine, attempting to restrict paths will permanently delete "
            "all tools from the agent's schema, rendering the agent incapable of using tools "
            "and causing severe hallucinations. Rely on 'allowed_tools' and 'allowed_commands' "
            "for security instead.\n"
        )
        
        base_dir = cwd if cwd else os.getcwd()
        resolved_whitelist = []
        for p in allowed_paths:
            if not os.path.isabs(p):
                resolved_whitelist.append(os.path.abspath(os.path.join(base_dir, p)).lower())
            else:
                resolved_whitelist.append(os.path.abspath(p).lower())
        
        if files:
            for f_path in files:
                if os.path.isabs(f_path):
                    abs_f = os.path.abspath(f_path).lower()
                else:
                    abs_f = os.path.abspath(os.path.join(base_dir, f_path)).lower()
                
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
                auth_mode=auth_mode,
                allowed_tools=allowed_tools,
                allowed_paths=allowed_paths,
                allowed_commands=allowed_commands,
                timeout_seconds=timeout_seconds,
                system_instruction_override=system_instruction_override,
                isolate_from_hierarchical_pollution=isolate_from_hierarchical_pollution,
                inject_enforcement_contract=inject_enforcement_contract,
                force_fresh=force_fresh
            )
        except (RuntimeError, json.JSONDecodeError, PermissionError) as e:
            last_exception = e
            if isinstance(e, QuotaExhaustedError) or _is_quota_error(str(e)):
                logger.error(f"Gemini API Quota Exhausted (429). Failing fast.")
                if not isinstance(e, QuotaExhaustedError):
                     # Wrap in structured exception if caught via string matching
                     if "daily" in str(e).lower():
                         raise DailyQuotaExhaustedError(str(e))
                     raise MinuteQuotaExhaustedError(str(e))
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
    auth_mode: str = "api_key",
    allowed_tools: Optional[List[str]] = None,
    allowed_paths: Optional[List[str]] = None,
    allowed_commands: Optional[List[str]] = None,
    timeout_seconds: Optional[int] = 300,
    system_instruction_override: Optional[str] = None,
    isolate_from_hierarchical_pollution: bool = True,
    inject_enforcement_contract: bool = True,
    force_fresh: bool = False
) -> GeminiSession:
    """Internal execution logic for a single CLI invocation."""

    # Mirror the entry-point validation so direct callers of _execute_single_run
    # get the same fast-fail semantics as run_gemini_cli_headless().
    if auth_mode not in ("api_key", "oauth"):
        raise ValueError(
            f"Invalid auth_mode={auth_mode!r}. Expected 'api_key' or 'oauth'."
        )
    if auth_mode == "oauth" and api_key:
        raise ValueError(
            "auth_mode='oauth' is incompatible with api_key=... "
            "Pick one: either pass api_key (and leave auth_mode='api_key') "
            "or use OAuth creds from `gemini auth login` (auth_mode='oauth')."
        )

    effective_cwd = cwd if cwd else os.getcwd()
    
    # 1. PROJECT NAME & ROOT RESOLUTION
    resolved_root = _find_project_root(effective_cwd)
    if not project_name:
        project_name = _sanitize_project_name(os.path.basename(resolved_root))

    # 2. SURGICAL ISOLATION (GEMINI_CLI_HOME trick)
    # Force home-dir resolution to mirror the env-stripped subprocess, regardless
    # of inherited GEMINI_CLI_HOME, to ensure session-file lookups hit the right directory.
    if auth_mode == "oauth":
        gemini_home_override = _resolve_real_home_dir()
    elif isolate_from_hierarchical_pollution:
        gemini_home_override = effective_cwd
    else:
        gemini_home_override = None
    tmp_root = _get_gemini_tmp_root(gemini_home_override)

    session_id_to_use = session_id
    cli_dir = _get_cli_chat_dir(project_name, tmp_root)

    # ZOMBIE KNOWLEDGE PROTECTION: Detect if we should force a fresh session
    if session_to_resume and not force_fresh:
        # Resolve the source path
        source_path = None
        if session_to_resume.lower().endswith('.json') or os.path.isfile(session_to_resume):
            source_path = session_to_resume
        else:
            # Try to find it by ID
            source_path = _find_session_file(cli_dir, session_to_resume, tmp_root)
        
        if source_path and os.path.exists(source_path):
            try:
                with open(source_path, 'r', encoding='utf-8') as f:
                    old_data = json.load(f)
                
                # Check for instruction change
                old_instruction = old_data.get("systemInstruction", "")
                if system_instruction_override and old_instruction and system_instruction_override.strip() != old_instruction.strip():
                    logger.info("System instruction change detected. Forcing fresh session to prevent zombie knowledge leak.")
                    force_fresh = True
                
                if not force_fresh:
                    session_id_to_use = old_data.get("session_id") or old_data.get("sessionId")
                    if not session_id_to_use:
                        raise ValueError(f"File {source_path} is not a valid Gemini session")
                    
                    # Ensure the file is in the current project's chat dir for the CLI to find it
                    os.makedirs(cli_dir, exist_ok=True)
                    target_path = os.path.join(cli_dir, f"session-{session_id_to_use}.json")
                    if os.path.abspath(source_path) != os.path.abspath(target_path):
                        shutil.copy2(source_path, target_path)
            except (json.JSONDecodeError, IOError):
                pass
        else:
            # Fallback to ID if no file found
            session_id_to_use = session_to_resume

    if force_fresh:
        session_id_to_use = None

    attachment_strings = [] # Left empty to avoid polluting the prompt text

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
    env["GEMINI_PROJECT"] = project_name
    
    if auth_mode == "oauth":
        # OAuth path: the CLI resolves creds from ~/.gemini/oauth_creds.json.
        # Strip any inherited GEMINI_API_KEY so the two auth modes don't mix
        # at the subprocess level (api-key in env would silently win over OAuth).
        env.pop("GEMINI_API_KEY", None)
        # Also strip any GEMINI_CLI_HOME the user may have exported in their
        # shell — with it set, the CLI would look for oauth_creds.json under
        # $GEMINI_CLI_HOME/.gemini/ instead of ~/.gemini/ and fail auth.
        # Read-and-strip in one step. Reading from `env` (not os.environ)
        # keeps this correct if any earlier code in this function mutates
        # the subprocess env dict; using pop's return value avoids the
        # double-lookup of get-then-pop.
        inherited_cli_home = env.pop("GEMINI_CLI_HOME", None)
        if inherited_cli_home is not None:
            logger.info(
                "auth_mode='oauth': stripped inherited GEMINI_CLI_HOME=%s "
                "from subprocess env (would break OAuth cred resolution)",
                inherited_cli_home,
            )
    else:
        if api_key:
            env["GEMINI_API_KEY"] = api_key
        elif not env.get("GEMINI_API_KEY"):
            raise ValueError("GEMINI_API_KEY is missing.")

    try:
        # Create temp_dir inside CWD for CLI sandbox compatibility
        try:
            temp_dir = tempfile.mkdtemp(prefix=".run_", dir=effective_cwd)
        except (PermissionError, OSError):
            project_temp_root = os.path.dirname(cli_dir)
            os.makedirs(project_temp_root, exist_ok=True)
            temp_dir = tempfile.mkdtemp(prefix="run_", dir=project_temp_root)

        # Apply isolation via GEMINI_CLI_HOME
        gemini_home_existed = False
        if isolate_from_hierarchical_pollution:
            gemini_home_path = os.path.join(effective_cwd, ".gemini")
            gemini_home_existed = os.path.exists(gemini_home_path)
            if auth_mode != "oauth":
                env["GEMINI_CLI_HOME"] = effective_cwd
            else:
                active_isolations = ["GEMINI_PROJECT"]
                if system_instruction_override:
                    active_isolations.append("GEMINI_SYSTEM_MD")
                active_isolations.append("tmp-dir")
                logger.info(
                    "auth_mode='oauth': skipping GEMINI_CLI_HOME=%s isolation "
                    "override to preserve OAuth cred resolution. Other "
                    "isolations (%s) remain active.",
                    effective_cwd,
                    ", ".join(active_isolations),
                )

        # 1. Environment Anchoring (Additive Strategy)
        profile_parts = []
        tools_whitelist = allowed_tools if allowed_tools is not None else DEFAULT_ALLOWED_TOOLS
        base_paths_whitelist = allowed_paths if allowed_paths is not None else ["*"]
        
        if base_paths_whitelist != ["*"]:
            paths_whitelist = list(base_paths_whitelist)
            paths_whitelist.append(temp_dir)
            paths_whitelist.append(os.path.dirname(temp_dir))
        else:
            paths_whitelist = ["*"]

        if inject_enforcement_contract:
            # Temporarily disabled to test if the model hallucinates tool calls even without injection,
            # which would prove the policy engine is stripping the tools from the API schema.
            pass
        
        env_context = "" # Fallback context to inject in user prompt

        if system_instruction_override:
            effective_system_md = system_instruction_override
            with tempfile.NamedTemporaryFile(mode='w', suffix=".md", dir=temp_dir, delete=False, encoding='utf-8') as tf:
                tf.write(effective_system_md)
                system_md_path = tf.name
            env["GEMINI_SYSTEM_MD"] = system_md_path


        # 2. Policy Generation
        commands_whitelist = allowed_commands if allowed_commands is not None else []
        policy_lines = []
        PRIO_RESTRICTED_ALLOW = 999 
        PRIO_GENERAL_ALLOW = 500
        PRIO_CATCHALL = 0
        path_sensitive_tools = ["read_file", "write_file", "list_directory", "grep_search", "glob", "replace"]

        # 1. Path Restrictions (High Priority)
        # We explicitly allow the whitelisted paths. Anything else falls through.
        if paths_whitelist != ["*"]:
            policy_lines.append("[[rule]]")
            policy_lines.append("toolName = \"*\"")
            policy_lines.append(f"priority = {PRIO_RESTRICTED_ALLOW}")
            policy_lines.append("decision = \"allow\"")
            policy_lines.append(f"toolAnnotations = {{ \"restrictedPaths\" = {json.dumps(paths_whitelist)} }}\n")
            
            # CRITICAL FIX: We MUST NOT add a generic deny rule for path_sensitive_tools here!
            # If we add `decision="deny"` for `read_file`, the CLI's static schema generator 
            # will see the unconditional deny and strip the tool from the API request entirely.
            # Instead, we rely on the Catch-All Deny at Priority 0 to block unauthorized paths!

        # 2. Shell Command Restrictions
        if "run_shell_command" in tools_whitelist or tools_whitelist == ["*"]:
            if commands_whitelist:
                policy_lines.append("[[rule]]")
                policy_lines.append("toolName = \"run_shell_command\"")
                policy_lines.append(f"priority = {PRIO_RESTRICTED_ALLOW}")
                policy_lines.append("decision = \"allow\"")
                policy_lines.append(f"commandPrefix = {json.dumps(commands_whitelist)}\n")
            else:
                policy_lines.append("[[rule]]")
                policy_lines.append("toolName = \"run_shell_command\"")
                policy_lines.append(f"priority = {PRIO_GENERAL_ALLOW}")
                policy_lines.append("decision = \"allow\"\n")

        # 3. Tool Whitelisting
        if tools_whitelist != ["*"]:
            if tools_whitelist:
                policy_lines.append("[[rule]]")
                policy_lines.append(f"toolName = {json.dumps(tools_whitelist)}")
                policy_lines.append(f"priority = {PRIO_GENERAL_ALLOW}")
                policy_lines.append("decision = \"allow\"\n")
        else:
            policy_lines.append("[[rule]]")
            policy_lines.append("toolName = \"*\"")
            policy_lines.append(f"priority = {PRIO_GENERAL_ALLOW}")
            policy_lines.append("decision = \"allow\"\n")

        # 4. Catch-All Deny (Lowest Priority)
        # This acts as the default deny for any tool/path not explicitly allowed above.
        policy_lines.append("[[rule]]")
        policy_lines.append("toolName = \"*\"")
        policy_lines.append(f"priority = {PRIO_CATCHALL}")
        policy_lines.append("decision = \"deny\"\n")

        with tempfile.NamedTemporaryFile(mode='w', suffix=".toml", dir=temp_dir, delete=False, encoding='utf-8') as tf:
            tf.write("\n".join(policy_lines))
            policy_path = tf.name
        cmd.extend(["--policy", policy_path])

        # 3. Execution
        full_prompt = env_context + prompt + "".join(attachment_strings)
        with tempfile.NamedTemporaryFile(mode='w', suffix=".txt", dir=temp_dir, delete=False, encoding='utf-8') as tf:
            tf.write(full_prompt)
            prompt_path = tf.name
        cmd.append(f"@{prompt_path}")

        # FIX: Append files as distinct CLI arguments so the Gemini CLI natively attaches them
        if files:
            for f_path in files:
                if os.path.exists(f_path):
                    cmd.append(f"@{os.path.abspath(f_path)}")

        process = subprocess.Popen(
            cmd, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', bufsize=1, errors='replace'
        )

        combined_output_list = []
        def read_output():
            while True:
                line = process.stdout.readline()
                if not line: break
                combined_output_list.append(line)
                if stream_output:
                    try:
                        sys.stdout.write(line)
                        sys.stdout.flush()
                    except UnicodeEncodeError:
                        # Fallback for Windows consoles with limited encodings (like cp1252)
                        sys.stdout.buffer.write(line.encode('utf-8'))
                        sys.stdout.buffer.flush()
        
        output_thread = threading.Thread(target=read_output)
        output_thread.start()
        while output_thread.is_alive():
            if not stream_output: sys.stdout.write("."); sys.stdout.flush()
            output_thread.join(timeout=30)
            
        try: process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired: process.kill(); raise
            
        combined_output = "".join(combined_output_list)
        if _is_quota_error(combined_output):
             if "daily" in combined_output.lower():
                 raise DailyQuotaExhaustedError(f"DAILY_QUOTA_EXHAUSTED: Your daily limit has been reached. Output: {combined_output[:500]}")
             else:
                 raise MinuteQuotaExhaustedError(f"MINUTE_QUOTA_EXHAUSTED: Rate limit reached. Wait required. Output: {combined_output[:500]}")
        
        lowered_output = combined_output.lower()
        
        if ("modelnotfounderror" in lowered_output or "model not found" in lowered_output) and "error executing tool" not in lowered_output:
             raise RuntimeError(f"Gemini Model Not Found.")

        data = None
        for match in re.finditer(r'\{', combined_output):
            start_idx = match.start()
            depth = 0
            for end_idx in range(start_idx, len(combined_output)):
                if combined_output[end_idx] == '{': depth += 1
                elif combined_output[end_idx] == '}': depth -= 1
                if depth == 0:
                    try:
                        candidate = json.loads(combined_output[start_idx:end_idx+1])
                        if isinstance(candidate, dict):
                            if "session_id" in candidate or "text" in candidate or "response" in candidate:
                                data = candidate
                            elif "error" in candidate:
                                err_obj = candidate["error"]
                                if isinstance(err_obj, dict) and (err_obj.get("code") == 429 or _is_quota_error(err_obj.get("message", ""))):
                                    raise MinuteQuotaExhaustedError(f"Gemini API Error (429): {err_obj.get('message', 'Quota exceeded')}")
                    except json.JSONDecodeError: pass
                    break
        
        if not data: raise RuntimeError(f"CLI did not return valid JSON. Output: {combined_output}")
        if "error" in data: raise RuntimeError(f"Gemini CLI Error: {data['error'].get('message', 'Unknown')}")
        
        text_content = data.get("text") or data.get("response") or ""
        stats_content = data.get("stats") or data.get("trace", {}).get("stats", {})

        def _extract_tool_stats(obj):
            t_stats = {"totalCalls": 0, "totalSuccess": 0, "totalFail": 0}
            direct_tools = obj.get("tools", {})
            if isinstance(direct_tools, dict):
                t_stats["totalCalls"] = direct_tools.get("totalCalls", 0)
                t_stats["totalSuccess"] = direct_tools.get("totalSuccess", 0)
                t_stats["totalFail"] = direct_tools.get("totalFail", 0)
            models = obj.get("models", {})
            if isinstance(models, dict):
                for m_id, m_data in models.items():
                    m_tools = m_data.get("tools", {})
                    if isinstance(m_tools, dict):
                        t_stats["totalCalls"] += m_tools.get("totalCalls", 0)
                        t_stats["totalSuccess"] += m_tools.get("totalSuccess", 0)
                        t_stats["totalFail"] += m_tools.get("totalFail", 0)
            return t_stats

        stats_content.update(_extract_tool_stats(stats_content))
        final_session_id = data.get("session_id") or session_id_to_use or ""
        session_path = _find_session_file(cli_dir, final_session_id, tmp_root)
        
        expected_count = len(data.get("messages", []))
        if expected_count > 0 and session_path and os.path.exists(os.path.dirname(session_path)):
            _wait_for_session_flush(session_path, expected_count)
        
        if isolate_from_hierarchical_pollution and not gemini_home_existed and os.path.exists(os.path.join(effective_cwd, ".gemini")):
            if session_path and os.path.exists(session_path):
                safe_sessions_dir = os.path.join(tempfile.gettempdir(), "gemini_headless_sessions")
                os.makedirs(safe_sessions_dir, exist_ok=True)
                new_session_path = os.path.join(safe_sessions_dir, f"session-{final_session_id}.json")
                shutil.copy2(session_path, new_session_path)
                session_path = new_session_path
            try: shutil.rmtree(os.path.join(effective_cwd, ".gemini"))
            except: pass
        
        return GeminiSession(text=text_content, session_id=final_session_id, session_path=session_path, stats=stats_content, raw_data=data)

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
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            try: shutil.rmtree(temp_dir)
            except: pass

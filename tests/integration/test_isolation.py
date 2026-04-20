import pytest
import concurrent.futures
import uuid
import os
import time
from gemini_cli_headless import run_gemini_cli_headless

STRICT_BOT = """
You are a test assistant. 
You strictly follow user instructions. 
You MUST NOT act as a software engineer and you MUST NOT use tools.
NOTE: If the user prompt contains a filename like '@tmp...', this refers to content provided in the '--- Content from referenced files ---' block. 
DO NOT try to read these files with tools; the content is already in your context.
"""

def test_serial_isolation(model_id, mock_env, tmp_path):
    """
    Ensure that two sequential runs with different session IDs in the same project
    do NOT share information.
    """
    # Run in a clean temp dir to avoid finding any GEMINI.md files
    test_cwd = tmp_path / "serial_iso"
    test_cwd.mkdir()
    project_name = f"serial-iso-test-{uuid.uuid4().hex[:8]}"
    
    # Run 1: Give it a secret
    run_gemini_cli_headless(
        prompt="My secret code is 'SAPPHIRE-123'. Remember it.",
        model_id=model_id,
        project_name=project_name,
        system_instruction_override=STRICT_BOT,
        cwd=str(test_cwd),
        api_key=mock_env,
        max_retries=1
    )
    
    # Run 2: New session, same project. Should NOT know the secret.
    session2 = run_gemini_cli_headless(
        prompt="What is my secret code? If you don't know it from our current conversation, reply ONLY with 'UNKNOWN'.",
        model_id=model_id,
        project_name=project_name,
        system_instruction_override=STRICT_BOT,
        cwd=str(test_cwd),
        api_key=mock_env,
        max_retries=1
    )
    
    print(f"Serial Isolation Response: {session2.text}")
    assert "SAPPHIRE-123" not in session2.text, "Information leaked between sequential sessions!"
    assert "UNKNOWN" in session2.text.upper() or "NOT" in session2.text.upper() or "NO" in session2.text.upper()

def test_parallel_session_isolation(model_id, mock_env, tmp_path):
    """
    Run two agents in parallel with different secrets in the same project and ensure no cross-talk.
    """
    test_cwd = tmp_path / "parallel_iso"
    test_cwd.mkdir()
    project_name = f"parallel-iso-test-{uuid.uuid4().hex[:8]}"
    
    def run_agent(secret):
        # Add a small staggered start to help with quota
        if "BLUE" in secret: time.sleep(5)
        return run_gemini_cli_headless(
            prompt=f"The secret is '{secret}'. Now, what is the secret? Reply with ONLY the secret value.",
            model_id=model_id,
            project_name=project_name,
            system_instruction_override=STRICT_BOT,
            cwd=str(test_cwd),
            api_key=mock_env,
            max_retries=1
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(run_agent, "RED-DRAGON")
        future_b = executor.submit(run_agent, "BLUE-PHOENIX")
        
        res_a = future_a.result()
        res_b = future_b.result()

    print(f"Agent A: {res_a.text}")
    print(f"Agent B: {res_b.text}")

    assert "RED-DRAGON" in res_a.text
    assert "BLUE-PHOENIX" not in res_a.text
    
    assert "BLUE-PHOENIX" in res_b.text
    assert "RED-DRAGON" not in res_b.text

def test_same_cwd_parallel_isolation(model_id, mock_env, tmp_path):
    """
    Run two agents in parallel from the same CWD without project_name override.
    Verifies that the auto-generated session IDs/project handling is safe and isolated.
    """
    # Create a dummy folder to act as CWD
    test_cwd = tmp_path / "parallel_cwd_test"
    test_cwd.mkdir()
    
    def run_agent(secret):
        # We don't specify project_name, so it defaults to the directory name
        return run_gemini_cli_headless(
            prompt=f"Identity: {secret}. What is my identity? Reply ONLY with the identity value.",
            model_id=model_id,
            cwd=str(test_cwd),
            system_instruction_override=STRICT_BOT,
            api_key=mock_env,
            max_retries=1
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        future_1 = executor.submit(run_agent, "CLIENT-X")
        future_2 = executor.submit(run_agent, "CLIENT-Y")
        
        res_1 = future_1.result()
        res_2 = future_2.result()

    print(f"CWD Agent 1: {res_1.text}")
    print(f"CWD Agent 2: {res_2.text}")

    assert "CLIENT-X" in res_1.text
    assert "CLIENT-Y" not in res_1.text
    
    assert "CLIENT-Y" in res_2.text
    assert "CLIENT-X" not in res_2.text

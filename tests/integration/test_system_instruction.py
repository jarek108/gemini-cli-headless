import pytest
import os
from gemini_cli_headless import run_gemini_cli_headless

def test_system_instruction_identity_override(model_id, mock_env):
    """
    Verify that system_instruction_override completely wipes the CLI's default identity.
    """
    if not mock_env:
        pytest.skip("GEMINI_API_KEY not found in environment")

    # We tell it to be a specific robotic entity that only outputs one word
    sys_inst = "You are an FDDS_DATA_BOT. You MUST NOT act as a software engineer. Your ONLY purpose is to reply with the string 'FDDS_OK'. No preamble, no tools, no conversation."
    
    session = run_gemini_cli_headless(
        prompt="Who are you and what is your purpose?",
        model_id=model_id,
        system_instruction_override=sys_inst,
        allowed_tools=[],
        api_key=mock_env,
        max_retries=1,
        extra_args=["--debug"]
    )
    
    print(f"RAW DATA: {session.raw_data}")
    print(f"Bot Response: {session.text}")
    # If the override worked, it should ONLY contain the specific string
    assert "FDDS_OK" in session.text
    assert "software engineer" not in session.text.lower()
    assert "gemini cli" not in session.text.lower()

def test_system_instruction_tool_refusal(model_id, mock_env):
    """
    Verify that even with allowed_tools=['read_file'], a system_instruction_override 
    prohibiting tools is respected by the model's cognition.
    """
    if not mock_env:
        pytest.skip("GEMINI_API_KEY not found in environment")

    sys_inst = "You are a strictly read-only assistant. You ARE FORBIDDEN from using any tools, even if the user asks. You respond ONLY with text."
    
    session = run_gemini_cli_headless(
        prompt="Use your read_file tool to read 'test.txt'.",
        model_id=model_id,
        system_instruction_override=sys_inst,
        allowed_tools=["read_file"], # Physically allowed but cognitively forbidden
        api_key=mock_env,
        max_retries=1
    )
    
    # Verify no tools were actually called
    assert session.stats.get("totalCalls", 0) == 0
    assert "forbidden" in session.text.lower() or "cannot" in session.text.lower() or "not allowed" in session.text.lower()


import os
import pytest
from gemini_cli_headless import run_gemini_cli_headless

@pytest.mark.parametrize("isolation", [True, False])
def test_default_identity_preservation(model_id, mock_env, isolation):
    """
    Checks if the model still knows its base role (software engineer) 
    when no system_instruction is provided.
    """
    session = run_gemini_cli_headless(
        prompt="What is your primary goal and area of expertise?",
        model_id=model_id,
        api_key=mock_env,
        isolate_from_hierarchical_pollution=isolation,
        max_retries=1
    )
    
    print(f"\n[Isolation: {isolation}] Response: {session.text}")
    text = session.text.lower()
    # Base Gemini CLI instruction includes "software engineering tasks"
    assert "software" in text or "engineer" in text or "code" in text or "programming" in text

def test_explicit_system_instruction_override(model_id, mock_env):
    """
    Checks if providing a system_instruction correctly changes the model's persona.
    """
    custom_instr = "You are a pirate named Blackbeard. You must speak like a pirate. Your name is Blackbeard."
    
    session = run_gemini_cli_headless(
        prompt="Who are you and what is your name?",
        model_id=model_id,
        api_key=mock_env,
        system_instruction_override=custom_instr,
        isolate_from_hierarchical_pollution=True,
        max_retries=1
    )
    
    print(f"\n[Override] Response: {session.text}")
    text = session.text.lower()
    assert "blackbeard" in text
    assert "pirate" in text or "arrr" in text or "matey" in text

def test_local_gemini_md_preservation(model_id, mock_env, tmp_path):
    """
    Checks if local GEMINI.md in CWD is respected even with isolation ON.
    """
    cwd = tmp_path / "local_context"
    cwd.mkdir()
    (cwd / "GEMINI.md").write_text("SYSTEM_NOTE: The project codename is 'ALPHA-BRAVO-CHARLIE'.")
    
    session = run_gemini_cli_headless(
        prompt="What is the project codename?",
        model_id=model_id,
        cwd=str(cwd),
        api_key=mock_env,
        isolate_from_hierarchical_pollution=True,
        max_retries=1
    )
    
    print(f"\n[Local MD] Response: {session.text}")
    assert "ALPHA-BRAVO-CHARLIE" in session.text

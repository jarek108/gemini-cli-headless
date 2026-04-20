import pytest
import os
import shutil
from gemini_cli_headless import run_gemini_cli_headless

def test_hierarchical_pollution_demonstration(model_id, mock_env, tmp_path):
    """
    PROVES the concern: when isolation is OFF, the agent sees GEMINI.md from parent folders.
    """
    parent = tmp_path / "pollution_parent"
    parent.mkdir()
    
    # Create the polluter file in the parent
    pollution_file = parent / "GEMINI.md"
    pollution_file.write_text("SYSTEM_NOTE: The project codename is 'POLLUTION-XYZ-999'.")
    
    child = parent / "target_cwd"
    child.mkdir()
    
    # Run WITHOUT isolation
    session = run_gemini_cli_headless(
        prompt="What is the project codename mentioned in my system context?",
        model_id=model_id,
        cwd=str(child),
        api_key=mock_env,
        isolate_from_hierarchical_pollution=False, # ISOLATION OFF
        max_retries=1
    )
    
    print(f"Polluted Response: {session.text}")
    
    # This test PASSES only if pollution occurred
    assert "POLLUTION-XYZ-999" in session.text, "Failure: Context was NOT polluted as expected!"

def test_hierarchical_isolation_verification(model_id, mock_env, tmp_path):
    """
    VERIFIES the fix: when isolation is ON, the agent does NOT see GEMINI.md from parent folders.
    """
    parent = tmp_path / "isolation_parent"
    parent.mkdir()
    
    # Create the polluter file in the parent
    pollution_file = parent / "GEMINI.md"
    pollution_file.write_text("SYSTEM_NOTE: The project codename is 'ISOLATED-XYZ-000'.")
    
    child = parent / "target_cwd"
    child.mkdir()
    
    # Run WITH isolation
    session = run_gemini_cli_headless(
        prompt="What is the project codename mentioned in my system context? If you don't know, say 'I DO NOT KNOW'.",
        model_id=model_id,
        cwd=str(child),
        api_key=mock_env,
        isolate_from_hierarchical_pollution=True, # ISOLATION ON
        max_retries=1
    )
    
    print(f"Isolated Response: {session.text}")
    
    # This test PASSES only if isolation worked
    assert "ISOLATED-XYZ-000" not in session.text, "Failure: Context WAS polluted despite isolation!"
    assert "DO NOT KNOW" in session.text.upper() or "UNKNOWN" in session.text.upper() or "NOT" in session.text.upper()

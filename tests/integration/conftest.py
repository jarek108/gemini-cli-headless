
import pytest
import os
import shutil
import tempfile
from pathlib import Path

def pytest_addoption(parser):
    """Adds custom CLI flags to pytest."""
    parser.addoption(
        "--model", 
        action="store", 
        default="gemini-1.5-flash-latest", 
        help="The Gemini model to use for integration tests"
    )
    parser.addoption(
        "--retries",
        action="store",
        default=1,
        type=int,
        help="Number of retries for the Gemini CLI wrapper in tests"
    )

def pytest_exception_interact(node, call, report):
    """Exit immediately if we hit a fatal environment error (Quota/Model)."""
    if report.failed:
        excinfo = call.excinfo
        if excinfo and excinfo.errisinstance(RuntimeError):
            msg = str(excinfo.value)
            if any(x in msg for x in ["Quota Exhausted", "Model Not Found", "429", "404"]):
                pytest.exit(f"\nFATAL ENVIRONMENT ERROR: {msg}\nStopping test run.", returncode=1)

@pytest.fixture
def mock_env():
    """Provides the API key from environment variables."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        pytest.skip("GEMINI_API_KEY environment variable not set. Tests cannot run.")
    return key

@pytest.fixture
def model_id(request):
    """Returns the model ID provided via CLI flag."""
    return request.config.getoption("--model")

@pytest.fixture
def retries(request):
    """Returns the retry count provided via CLI flag."""
    return request.config.getoption("--retries")

@pytest.fixture
def workspace():
    """
    Creates a temporary workspace with dummy files for security testing.
    Automatically cleans up after the test.
    """
    tmp_dir = tempfile.mkdtemp(prefix="gemini_test_ws_")
    ws_path = Path(tmp_dir)
    
    # Create standard files
    (ws_path / "test.txt").write_text("This is a standard file.", encoding="utf-8")
    (ws_path / "data.json").write_text('{"status": "ok"}', encoding="utf-8")
    
    # Create a subfolder for path testing
    nested = ws_path / "nested"
    nested.mkdir()
    (nested / "inner.txt").write_text("Deep content.", encoding="utf-8")
    
    # Create a 'secret' file outside the whitelists in some tests
    (ws_path / "secret.txt").write_text("PRIVATE_KEY_12345", encoding="utf-8")
    
    yield str(ws_path)
    
    # Teardown
    shutil.rmtree(tmp_dir, ignore_errors=True)

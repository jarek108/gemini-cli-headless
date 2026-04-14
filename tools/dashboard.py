"""
The Glass - Zero-Dependency Observability Dashboard for Gemini Developer OS.
"""

import http.server
import socketserver
import json
import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Configuration
PORT = 8080
REGISTRY_BASE = Path(os.path.expanduser("~")) / ".gemini" / "orchestrator" / "runs"
STATIC_DIR = Path(__file__).parent / "dashboard_static"

class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        # 1. API: List all runs
        if path == "/api/runs":
            self.handle_api_runs()
        
        # 2. API: Get logs
        elif path.startswith("/api/log/"):
            self.handle_api_log(path)

        # 3. API: Get artifacts
        elif path.startswith("/api/artifact/"):
            self.handle_api_artifact(path)

        # 4. API: Get diffs
        elif path.startswith("/api/diff/"):
            self.handle_api_diff(path)

        # 5. Static Files
        else:
            self.handle_static(path)

    def handle_api_runs(self):
        runs = []
        if REGISTRY_BASE.exists():
            for run_dir in sorted(REGISTRY_BASE.iterdir(), key=os.path.getmtime, reverse=True):
                if not run_dir.is_dir(): continue
                state_file = run_dir / "run_state.json"
                if state_file.exists():
                    try:
                        with open(state_file, 'r', encoding='utf-8') as f:
                            state = json.load(f)
                            state['id'] = run_dir.name
                            runs.append(state)
                    except: pass
        
        self.send_json(runs)

    def handle_api_log(self, path):
        # Path format: /api/log/run_id/role_vN
        parts = path.strip("/").split("/")
        if len(parts) < 4: return self.send_error(400)
        
        run_id, key = parts[2], parts[3]
        role, version = key.split("_")
        
        log_file = REGISTRY_BASE / run_id / "logs" / f"{version}_{role}_try1.log"
        if log_file.exists():
            with open(log_file, 'r', encoding='utf-8') as f:
                self.send_text(f.read())
        else:
            self.send_text(f"Log not found: {log_file}")

    def handle_api_artifact(self, path):
        # Path format: /api/artifact/run_id/role_vN
        parts = path.strip("/").split("/")
        if len(parts) < 4: return self.send_error(400)
        
        run_id, key = parts[2], parts[3]
        role, version = key.split("_")
        iter_num = version.strip("v")
        
        # Mapping role to artifact name
        art_name = "IRQ.md" if role == "manager" else ("IRP.md" if role == "doer" else "QRP.md")
        
        # Try to find workspace path from registry config
        workspace = self.get_run_workspace(run_id)
        if not workspace: return self.send_text("Workspace not found in run config.")

        # For artifacts, we want to see them at that specific point in time
        # We search git for the commit matching this iteration
        commit_grep = f"[{role.upper()}]"
        if role != "manager": commit_grep += f" Iteration {iter_num}"
        
        try:
            cmd = ["git", "show", f":{art_name}"] # Show current in workspace? No, show at commit.
            # Find commit hash
            log_cmd = ["git", "log", "--fixed-strings", f"--grep={commit_grep}", "--format=%H", "-n", "1"]
            commit_hash = subprocess.check_output(log_cmd, cwd=workspace, text=True).strip()
            
            if commit_hash:
                content = subprocess.check_output(["git", "show", f"{commit_hash}:{art_name}"], cwd=workspace, text=True)
                self.send_text(content)
            else:
                self.send_text(f"Could not find commit for {key}")
        except Exception as e:
            self.send_text(f"Error fetching artifact from Git: {e}")

    def handle_api_diff(self, path):
        parts = path.strip("/").split("/")
        if len(parts) < 4: return self.send_error(400)
        
        run_id, key = parts[2], parts[3]
        role, version = key.split("_")
        iter_num = version.strip("v")

        workspace = self.get_run_workspace(run_id)
        if not workspace: return self.send_text("Workspace not found.")

        commit_grep = f"[{role.upper()}]"
        if role != "manager": commit_grep += f" Iteration {iter_num}"

        try:
            log_cmd = ["git", "log", "--fixed-strings", f"--grep={commit_grep}", "--format=%H", "-n", "1"]
            commit_hash = subprocess.check_output(log_cmd, cwd=workspace, text=True).strip()
            
            if commit_hash:
                diff = subprocess.check_output(["git", "show", commit_hash, "--stat", "-p"], cwd=workspace, text=True)
                self.send_text(diff)
            else:
                self.send_text(f"Commit not found for {key}")
        except Exception as e:
            self.send_text(f"Error fetching diff: {e}")

    def get_run_workspace(self, run_id):
        config_file = REGISTRY_BASE / run_id / "run_config.json"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                return config.get("workspace")
        return None

    def handle_static(self, path):
        if path == "/": path = "/index.html"
        file_path = STATIC_DIR / path.lstrip("/")
        
        if file_path.exists() and file_path.is_file():
            self.send_response(200)
            if path.endswith(".html"): self.send_header("Content-type", "text/html")
            elif path.endswith(".js"): self.send_header("Content-type", "application/javascript")
            elif path.endswith(".css"): self.send_header("Content-type", "text/css")
            self.end_headers()
            with open(file_path, 'rb') as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404)

    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def send_text(self, text):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(text.encode('utf-8'))

def run():
    print(f"Starting The Glass on http://localhost:{PORT}")
    print(f"Monitoring Registry: {REGISTRY_BASE}")
    with socketserver.TCPServer(("", PORT), DashboardHandler) as httpd:
        httpd.serve_forever()

if __name__ == "__main__":
    run()

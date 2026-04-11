# The Multi-Instance Project Architecture

A key challenge in multi-agent orchestration is **Resource Interference**. While cloning a Git repository prevents code conflicts, it does not prevent system-level collisions. If two worker agents run integration tests that bind to port `8000` simultaneously, the second worker will crash with an `EADDRINUSE` error. The QA agent will incorrectly blame the Doer's code, wasting iterations and budget.

To solve this, the Autonomous Developer OS treats a single project not as a single codebase, but as a **Container for Instances**.

## 1. The Instance Container Structure

Instead of creating "worker sandboxes" in a separate, messy global directory, workers are strictly encapsulated within their parent project's directory. 

```text
projects/
└── fdds/                           # The Project Container
    ├── .gemini.md                  # Project Manifest (Instructions for the Manager)
    ├── instance_main/              # (Optional) The pristine production codebase
    │   ├── src/
    │   └── .git/
    │
    ├── instance_worker_1/          # Active Instance for Task A (Branch: feature/db)
    │   ├── src/                    # Isolated copy of the codebase
    │   ├── .git/                   # Isolated Git worktree
    │   └── .agent_run/             # Hidden folder for this specific worker's state
    │       ├── run_config.json     # Task spec and dynamic resource allocations
    │       ├── IRP_v1.md           # Implementation Report (Doer artifact)
    │       ├── QRP_v1.md           # QA Report (Auditor artifact)
    │       ├── .doer_session.json  # Doer's memory
    │       └── .qa_session.json    # QA's memory
    │
    └── instance_worker_N/          # Active Instance for Task B (Branch: feature/css)
        ├── src/
        ├── .git/
        └── .agent_run/
```

### Key Benefits of this Structure:
1. **Scoping & Encapsulation:** If you delete the `fdds/` directory, you delete the project and all its active workers cleanly. There is no orphaned state left in a global `sandboxes` folder.
2. **Clean Codebases:** Implementation artifacts (`IRP.md`, `QRP.md`, session JSONs) do not pollute the root of the source code (`src/`). They are cleanly isolated in the `.agent_run/` directory. When the code is ready to be merged, there is no need to update `.gitignore` or clean up temporary files.

## 2. The Project Manifest (`.gemini.md`)

The Manager (acting as DevOps) reads the `.gemini.md` file located at the root of the project container. This file defines the project's rules, how to create/destroy instances, and what resources to manage.

```markdown
# FDDS Project Manifest

## Instance Lifecycle
- **Create:** `git worktree add ../instance_{worker_name} -b feature/{worker_name}`
- **Destroy:** `git worktree remove ../instance_{worker_name}`

## Resource Management
- **Ports:** Requires dynamic allocation. The main app uses `8000`. Workers must be assigned unique ports via the `PORT` environment variable to run concurrent tests.
- **Database:** Uses a local SQLite file (`data/dev.db`). Safe for parallel instances as each instance has its own physical copy of the file.
- **Hardware Mutex:** `false`. This project is lightweight. Parallel instances are fully supported.
```

## 3. Handling Unforeseen Interferences

When the Manager receives a task and creates an instance (e.g., `instance_worker_1`), it dynamically assigns resources based on the manifest. 

For example, the Manager generates a `run_config.json` inside `instance_worker_1/.agent_run/` that includes:
```json
{
  "environment_variables": {
    "PORT": "8001"
  }
}
```

### The "Hardware Mutex" (Single-Instance Constraints)
In some projects (e.g., a massive Unity 3D project or a codebase requiring exclusive GPU access for ML training), true multi-instancing is physically impossible without crashing the machine.

If the `.gemini.md` manifest declares `Hardware Mutex: true`, the Manager alters its behavior. If you ask it to perform two tasks, it will **not** create `instance_worker_2`. Instead, it will create a queue and run the orchestrator loop strictly sequentially within `instance_main` (or a single `instance_worker`), notifying you: *"I have queued Feature B. This project requires exclusive hardware access and cannot be parallelized."*
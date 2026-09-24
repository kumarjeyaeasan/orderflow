# SETUP — VS Code + Claude Code from scratch

This guide was written in September 2026. Installers and versions change, so if any command fails,
use the linked official page as the source of truth.

**Time needed:** about 45–90 minutes, mostly downloads.
**Hardware:** 16 GB RAM recommended (8 GB works through about Phase 5), and 30 GB+ free disk space.

---

## Step 1 — Choose your OS path

| OS | Path |
|---|---|
| **macOS** | Install everything natively. |
| **Windows** | **Use WSL2 (Ubuntu).** Keep the project *inside* the Linux filesystem (`~/code/...`, not `/mnt/c/...`), because file I/O and Docker volumes are much faster there. VS Code runs on Windows and connects into WSL. |
| **Linux** | Install everything natively. |

**Windows only: install WSL2 first.** In an Administrator PowerShell, run:
```powershell
wsl --install
```
Reboot, open "Ubuntu" from the Start menu, and create a Linux username and password.
Docs: https://learn.microsoft.com/en-us/windows/wsl/install

> From here on, Windows users run every terminal command inside the **Ubuntu (WSL)** terminal unless stated otherwise.

---

## Step 2 — Install core tools

### 2.1 Git
- **macOS:** `xcode-select --install` (or `brew install git`)
- **Ubuntu/WSL:** `sudo apt update && sudo apt install -y git build-essential curl unzip`
  (`build-essential` provides `make`, which the project uses as its command runner. On macOS, `make` comes with the Xcode tools.)

Then configure it:
```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
```

### 2.2 Docker
- **macOS / Windows:** Install **Docker Desktop**. On Windows, enable the *WSL 2 backend* and turn on
  *Resources → WSL Integration* for Ubuntu (https://docs.docker.com/desktop/features/wsl/).
  In Settings → Resources, give Docker **at least 6–8 GB of memory**.
  Check Docker Desktop's licence terms if you use it commercially.
- **Linux:** Install Docker Engine plus the Compose plugin from https://docs.docker.com/engine/install/,
  then run `sudo usermod -aG docker $USER` and log out and back in.

Verify:
```bash
docker version
docker compose version
docker run --rm hello-world
```

### 2.3 uv (Python package and project manager) and Python 3.12
```bash
# macOS / Linux / WSL
curl -LsSf https://astral.sh/uv/install.sh | sh
# restart the terminal, then:
uv python install 3.12
uv --version
```
Docs: https://docs.astral.sh/uv/
(uv installs and manages Python for you, so no separate Python install is needed.)

### 2.4 Later-phase tools (install when you reach them)
| Tool | Needed from | Link |
|---|---|---|
| kind + kubectl | Phase 8 | https://kind.sigs.k8s.io/ |
| Helm | Phase 8 | https://helm.sh/docs/intro/install/ |
| Linkerd CLI | Phase 8 | https://linkerd.io/2/getting-started/ |
| Temporal CLI (optional) | Phase 5 stretch | https://docs.temporal.io/develop/python |

---

## Step 3 — Install VS Code
Download it from https://code.visualstudio.com/ (version **1.94.0 or later** is required by the Claude Code extension).

- **macOS:** open the Command Palette (`Cmd+Shift+P`) → *Shell Command: Install 'code' command in PATH*.
- **Windows:** install on Windows (not inside WSL), then install the **WSL** extension (`ms-vscode-remote.remote-wsl`).
  From the Ubuntu terminal, `code .` opens VS Code connected to WSL.
  Docs: https://code.visualstudio.com/docs/remote/wsl

---

## Step 4 — Install Claude Code

### 4.1 VS Code extension (main interface)
In VS Code, press `Ctrl+Shift+X` (`Cmd+Shift+X` on Mac), search **"Claude Code"** (publisher: Anthropic;
ID `anthropic.claude-code`), and click **Install**. If it doesn't appear, run *Developer: Reload Window*.

- **Windows + WSL:** install the extension while VS Code is connected to WSL, so it runs on the Linux side.
- **Requirement:** a paid Claude subscription (Pro, Max, Team, or Enterprise) or a Claude Console account. You sign in on first use; no API key is needed with a subscription.

### 4.2 CLI (optional but useful)
The extension bundles its own copy for the chat panel. To also run `claude` in the integrated terminal:
```bash
curl -fsSL https://claude.ai/install.sh | bash     # macOS / Linux / WSL
claude --version
```

Docs:
- VS Code extension: https://code.claude.com/docs/en/vs-code
- Setup and alternative installers: https://code.claude.com/docs/en/setup

### 4.3 Sign in
Click the **Spark icon** (Activity Bar, or the editor toolbar when a file is open) and follow the sign-in prompt.

---

## Step 5 — Create the project and add these files
```bash
mkdir -p ~/code/orderflow && cd ~/code/orderflow

# macOS / Linux: unzip from your Downloads folder
unzip ~/Downloads/orderflow-pack.zip -d .

# Windows + WSL: the Windows Downloads folder is visible from Ubuntu under /mnt/c
unzip /mnt/c/Users/<YourWindowsUser>/Downloads/orderflow-pack.zip -d .

ls -la      # you should see CLAUDE.md, README.md, SETUP.md, docs/, .vscode/, .gitignore
git init
git add -A
git commit -m "chore: project brief, roadmap and Claude Code instructions"
code .
```
Unzip from the terminal as shown. Finder and Explorer hide dot-files, so `.vscode/` and `.gitignore` can get lost
if you copy files by hand.

When VS Code opens, accept the prompt to **install recommended extensions**. They come from `.vscode/extensions.json`.

> **Do not run `/init`.** `CLAUDE.md` is already written for this project; `/init` would only suggest edits to it.

## Step 6 — Verify Claude Code sees the project instructions
1. Open the Claude Code panel.
2. Type `/context` and check that `CLAUDE.md` (and the imported `docs/PROGRESS.md`) appear under memory files.
3. Ask: *"In 5 lines, what are we building and what are your working rules?"* The answer should mention OrderFlow,
   one phase at a time, explaining before coding, and GUIDED/BUILD modes. If it doesn't, check that
   `CLAUDE.md` is at the workspace root, the folder you opened.

---

## Step 7 — First real prompt (starts Phase 0)
```
Read docs/PROJECT_BRIEF.md and Phase 0 in docs/ROADMAP.md.
MODE: BUILD. First step only: uv workspace, Makefile (targets listed in CLAUDE.md), ruff/mypy/pytest config,
.env.example, monolith/ skeleton with the six modules and health endpoints, infra/compose/docker-compose.yml
(postgres + monolith), Alembic setup and seed data.
Show me the plan first and wait for approval. After implementing, run make up, make test and make lint
and show me the output.
```

After that, follow `docs/SESSION_PLAYBOOK.md` for every session.

---

## Troubleshooting quick list
| Symptom | Likely fix |
|---|---|
| `docker: permission denied` (Linux/WSL) | Add your user to the docker group, then log out and in again; on WSL, check Docker Desktop's WSL integration |
| Very slow builds on Windows | The project is under `/mnt/c/...`; move it into `~/` inside WSL |
| Claude ignores project rules | Run `/context` to confirm `CLAUDE.md` loaded; keep it under ~200 lines |
| Containers killed or restarting | Increase Docker memory; keep optional profiles (Kafka, observability) off |
| Extension missing after install | Command Palette → *Developer: Reload Window* |
| `make: command not found` | Ubuntu/WSL: `sudo apt install build-essential`; macOS: `xcode-select --install` |
| Port already in use (8000–8010, 5432, 5672) | Stop the other process, or change the host port mapping in Compose |

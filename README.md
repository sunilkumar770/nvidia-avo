# 🚀 NVIDIA AVO (Autonomous Validation Orchestrator)

> **Persistent Memory + Terminal Execution Grounding + Loop Stagnation Escape** for Antigravity, Claude Code, Cursor, Windsurf, and Gemini CLI.

Modeled on **NVIDIA's Agentic Variation Operators** research, `nvidia-avo` is a zero-dependency, standard-library Python harness that guarantees high accuracy and prevents failure loops on long-horizon software engineering tasks.

---

## ⚡ Quick 1-Command Installation

### For Antigravity & Claude Code (Any Project)
Open terminal in your project directory and run:

```bash
# Option 1: Direct via Python
python -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/sunilkumar770/nvidia-avo/main/install.py').read())"
```

```bash
# Option 2: Clone & Install
git clone https://github.com/sunilkumar770/nvidia-avo.git
cd nvidia-avo
python install.py
```

```bash
# Option 3: Via Pip
pip install nvidia-avo
avo install --target all
```

---

## 🛠️ What Gets Installed

Executing the installer configures your environment with zero friction:

| File / Target | Location | Purpose |
| :--- | :--- | :--- |
| **Global Rules** | `~/.gemini/config/rules/avo-global.md` | Injects AVO rules into all global Antigravity sessions |
| **Global Agents** | `~/.gemini/config/agents/avo_worker/` & `avo_supervisor/` | Registers `avo_worker` and `avo_supervisor` agents globally |
| **Project Rules** | `AGENTS.md` & `GEMINI.md` | Workspace-level active AVO protocols |
| **Claude Code Rules** | `CLAUDE.md` & `.agentrules` | Claude Code CLI rules & hooks |
| **Memory Engine** | `.avo/avo.py` & `.agent_memory.json` | Local session memory & fingerprint tracker |

---

## 🧠 Core Principles

1. **Memory First**: Check `.agent_memory.json` (`avo summary`) before starting tasks. Never repeat logged dead ends.
2. **Execution Grounding**: Every code edit MUST be verified with live terminal execution (`npm test`, `pytest`, etc.).
3. **Persistent Logging**: Write outcome hashes to memory (`avo log`). Save durable project facts (`avo fact`).
4. **Stagnation Loop Escape**: If 3 consecutive actions produce the same error fingerprint, `avo check` flags **STAGNATION** and forces a strategy pivot.

---

## 📊 CLI Command Reference

```bash
# View session memory summary
avo summary

# Run system diagnostic check
avo doctor

# Check loop stagnation (Exit Code 0 = OK, Exit Code 1 = Stagnated)
avo check

# Save a durable project fact
avo fact "Backend runs on port 8080"

# Log an attempt
avo log --task "Fix Auth Loop" --action "Edit auth.ts" --output "Pass 12/12" --status success
```

---

## 🧪 Verification & Test Suite

Run the built-in unit test suite to verify 100% operational integrity:

```bash
python test_avo.py
```

---

## 📄 License
[MIT License](LICENSE)

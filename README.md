# 🚀 NVIDIA AVO + DeepSeek Harness (DSH) — Hybrid Execution Engine

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.8+](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![Antigravity Compatible](https://img.shields.io/badge/Antigravity-Compatible-green.svg)](https://antigravity.google)
[![Claude Code Compatible](https://img.shields.io/badge/Claude%20Code-Compatible-orange.svg)](https://code.claude.com)
[![DeepSeek Harness](https://img.shields.io/badge/DSH-Hybrid%20Engine-purple.svg)](https://github.com/deepseek-ai)

> **Macro Supervision (NVIDIA AVO) + Micro Execution (DeepSeek Harness / DSH)** for **Google Antigravity**, **Claude Code**, **Cursor**, **Windsurf**, and **Gemini CLI**. Zero model downloads required — wraps around any LLM backend (Gemini 3.6/3.5, Claude Opus/Sonnet, GPT-4o).

---

## 🏛️ Architecture: The AVO + DSH Hybrid Pipeline

The hybrid pipeline splits agent responsibilities across two complementary layers:

* **NVIDIA AVO (Macro Layer):** Operates as the **supervisor & state optimizer**. It maintains long-term memory (`.agent_memory.json`), monitors execution progress, tracks token budget efficiency, and intervenes if an agent gets stuck in loops.
* **DeepSeek Harness / DSH (Micro Layer):** Operates as the **modular, plugin-driven execution engine**. It exposes granular tool execution, sub-agents, session logging, and flexible tool invocation modes.

```
  [ Antigravity IDE / Workspace ]
                 │
                 ▼
      ┌─────────────────────┐
      │  A.V.O. Supervisor  │ ◄── (Monitors Stagnation & Long-Horizon Memory)
      └──────────┬──────────┘
                 │ (Delegates Task Execution)
                 ▼
      ┌─────────────────────┐
      │ DeepSeek Harness    │
      │ (Cordis DSH Engine) │ ◄── (Executes Files, Shell Commands, & Tools)
      └──────────┬──────────┘
                 │
                 ▼
  [ Test / Compiler Output ] ──► [ AVO Log & Evaluate ]
```

---

## ⚡ 1-Command Plug-and-Play Installation

### Option A: Universal Remote Installer (Recommended)
Open any project folder in your terminal and run:

```bash
python -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/sunilkumar770/nvidia-avo/main/install.py').read())"
```

### Option B: Clone & Install locally
```bash
git clone https://github.com/sunilkumar770/nvidia-avo.git
cd nvidia-avo
python install.py
```

### Option C: Optional DSH CLI Global Setup
```bash
npm install -g @deepseek-ai/dsh
```

---

## 🐍 Hybrid Engine API & CLI Usage (`hybrid_engine.py`)

Run tasks through the hybrid orchestrator directly:

```bash
# Execute hybrid task via avo CLI
avo hybrid "Refactor main module and verify unit tests pass" --mode standard

# Or run hybrid_engine.py directly
python hybrid_engine.py "Fix authentication loop in middleware"
```

### Python API Integration
```python
from hybrid_engine import HybridAVODSHEngine

engine = HybridAVODSHEngine(workspace_path=".")
success, output = engine.execute_dsh_step("Run full test suite", mode="standard")
```

---

## 🧠 The 4 Core Principles of AVO + DSH

1. **Memory First (`.agent_memory.json`)**: Before attempting any task, AVO loads attempt history, environment facts, and failure fingerprints to block repeated dead ends.
2. **DSH Granular Tool Execution**: DSH (or subshell fallback) handles file-editing, script executions, and granular tool calls.
3. **Persistent Session Hashing**: Outputs are hashed with 12-character SHA-1 fingerprints (e.g. `be71d557286c`).
4. **Stagnation Loop Escape**: If 3 consecutive actions yield identical error fingerprints, AVO flags **STAGNATION** and forces an intervention strategy redirect.

---

## 💻 Command Line Interface (CLI)

```bash
# View session memory summary & dead ends
avo summary

# Run diagnostic health check (AVO + DSH)
avo doctor

# Run hybrid orchestration task
avo hybrid "Run unit tests"

# Check for loop stagnation
avo check

# Store a durable project fact
avo fact "Backend runs on port 8080"
```

---

## 🧪 Automated Test Suite

Verify 100% operational integrity on your machine:

```bash
python test_avo.py
```

---

## 📄 License & Attribution

- **License**: [MIT License](LICENSE)
- **Research Reference**: Inspired by NVIDIA Corporation's *Agentic Variation Operators (AVO)* research architecture and DeepSeek Harness (DSH) Cordis runtime.
- **Maintainer**: [Sunil Kumar](https://github.com/sunilkumar770)

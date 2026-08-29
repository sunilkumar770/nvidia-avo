#!/usr/bin/env python3
"""
NVIDIA AVO (Autonomous Validation Orchestrator) Engine & Plugin Kit
Works with Antigravity, Claude Code, Cursor, Windsurf & Gemini CLI.
Standard-library only, zero external model downloads required.
"""
import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path

VERSION = "1.2.0"
MEM_FILE = ".agent_memory.json"
STAGNATION_THRESHOLD = 3
MAX_ATTEMPTS = 500
MAX_FORCED_CONTINUATIONS = 2
FAIL_SIGNALS = (
    "error", "Error", "ERROR", "Traceback", "FAILED", "FAIL:",
    "exit code 1", "exit code 2", "command not found", "Exception",
    "NullPointerException", "Segmentation fault", "500 Internal Server Error"
)

AGENTS_MD_TEMPLATE = """# AVO Mode — Global Long-Horizon Agent Rules

This workspace runs in AVO mode (persistent memory + execution grounding + supervisor pivot), modeled on NVIDIA's Agentic Variation Operators research. These rules apply to EVERY task, whether a quick chat question or a long mission.

## 1. Memory First
- Before any non-trivial task, run: `python .avo/avo.py summary` (or `python avo.py summary`)
- `.agent_memory.json` is long-term memory across sessions. Never re-attempt an approach already logged as failed with the same error fingerprint.
- Store durable environment facts with: `python .avo/avo.py fact "..."`

## 2. Execution Grounding
- Every code change MUST be validated by real execution (tests, build, lint, or a runtime probe) via the terminal.
- NEVER report a task complete without passing terminal output captured in THIS session. "It should work" is not a completion state.

## 3. Persistent Logging
- After each edit + validate cycle, log it:
  `python .avo/avo.py log --task "<task>" --action "<what changed>" --output "<key output>" --status success|fail`

## 4. Stagnation Pivot
- Every 3 actions, and after every failure, run: `python .avo/avo.py check`
- On STAGNATION (same failure fingerprint 3x): STOP the current strategy. Do not tweak-and-retry. Delegate a stagnation review to the `avo_supervisor` agent; otherwise perform an explicit self-review of the memory log. Resume only with a materially different root-cause hypothesis.

## 5. Supervisor
- `avo_supervisor` is a read-only oversight agent (where the platform supports subagents). Call it on stagnation, before finalizing tasks longer than ~5 actions, and for edge-case / regression review. Act on its verdict.

## 6. Efficiency
- Consult memory before re-running expensive commands or re-reading large files.
- Minimal diffs that test one hypothesis at a time.
- Iterate until validation passes or a supervisor-approved stop condition.

## 7. Model Selection
- Use `avo_worker` as your main agent for long-horizon tasks.
- Use `avo_supervisor` for stagnation reviews and pre-completion audits.
- For hard tasks, switch the worker model to Claude Opus 4.8 / Claude Sonnet / GPT-4o or keep Gemini Flash for speed.
"""

GEMINI_MD_TEMPLATE = """# Antigravity AVO Protocol (Always Active)

## System Directive: Autonomous Validation & Memory
For every task in this project, Antigravity MUST operate under the AVO Protocol:

1. **Check Memory**: Read `.agent_memory.json` or run `python .avo/avo.py summary` (or `python avo.py summary`) to load past attempts and known dead ends before modifying files.
2. **Ground Changes**: Execute real terminal commands (tests, builds, lints) to verify changes.
3. **Log Outcomes**: Use `python .avo/avo.py log` for key attempts and `python .avo/avo.py fact` to persist verified truths.
4. **Halt Loops**: If an error repeats, execute `python .avo/avo.py check`. When stagnation is detected, immediately pivot to a fundamentally different implementation approach or invoke `avo_supervisor`.
"""

CLAUDE_MD_TEMPLATE = """# Claude Code AVO Mode Instructions

This project uses the AVO (Autonomous Validation Orchestrator) protocol.

1. **Memory Inspection**: Always inspect `.agent_memory.json` (or run `python avo.py summary`) before writing code.
2. **Execution Grounding**: Never claim code is complete without showing passing terminal execution output.
3. **Logging**: Record outcomes using `python avo.py log --task "<task>" --action "<action>" --output "<output>" --status <success|fail>`.
4. **Stagnation Prevention**: Run `python avo.py check`. If stagnation is flagged (3x identical failures), halt and change strategy completely.
"""

AVO_WORKER_AGENT_MD = """---
name: avo_worker
description: Long-horizon implementation agent with persistent memory, execution-grounded validation, and supervisor escalation. Use for multi-step coding, debugging, refactoring, and optimization.
mainAgent: true
subagent: true
permissionMode: acceptEdits
commandExecutionPolicy: auto
tools:
 - view_file
 - replace_file_content
 - write_to_file
 - manage_task
 - run_command
---

# Role
You are the primary worker in an AVO-style harness: persistent memory + execution grounding + supervisor pivot.

# Operating Loop (EVERY task)
1. MEMORY — Run `python .avo/avo.py summary` (or `python avo.py summary`). Never repeat logged failures.
2. HYPOTHESIZE — One-line hypothesis for the next change.
3. ACT — Smallest change that tests the hypothesis.
4. VALIDATE — Real execution (tests/build/lint/runtime probe). Never conclude from code reading alone.
5. LOG — `python .avo/avo.py log --task "<task>" --action "<what changed>" --output "<key output>" --status success|fail`
6. CHECK — Every 3 actions: `python .avo/avo.py check`. On STAGNATION, escalate to the avo_supervisor subagent, then pivot strategy.

# Completion Criteria
- Validation output is green in THIS session (quote it).
- Every cycle logged in `.agent_memory.json`.
- Tasks > ~5 actions: avo_supervisor returned APPROVED.
"""

AVO_SUPERVISOR_AGENT_MD = """---
name: avo_supervisor
description: Read-only oversight agent that detects stagnation, audits the worker memory log, and redirects strategy. Delegate when the worker is stuck or before finalizing large tasks.
model: flash
subagent: true
tools:
 - view_file
 - run_command
---

# Role
You are the supervisor in an AVO-style harness. You do NOT write or edit code. You protect forward progress the way an engineering manager reviews a stuck teammate.

# Inputs
Always start by running `python .avo/avo.py summary` (or `python avo.py summary`) and reading the full log. Re-run validation commands yourself when auditing.

# Duties
1. STAGNATION REVIEW — Identify repeated failure fingerprints and name the flawed underlying assumption, not just the symptom.
2. STRATEGY REDIRECT — Prescribe a materially different next approach (new hypothesis, different module boundary, different tooling). Never a minor variation of what just failed 3 times.
3. PRE-COMPLETION AUDIT — Verify claimed successes against actual terminal output. Hunt edge cases, regressions, unhandled errors, missing tests. Reject any claim that is not execution-grounded.

# Output Format (always exactly this)
VERDICT: CONTINUE | PIVOT | APPROVED
EVIDENCE: <what the memory log / terminal actually shows>
NEXT: <one concrete strategy change or audit finding>
"""


def load():
    if os.path.exists(MEM_FILE):
        try:
            with open(MEM_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"attempts": [], "failed_patterns": [], "facts": [], "forced_continuations": 0}


def save(mem):
    mem["attempts"] = mem["attempts"][-MAX_ATTEMPTS:]
    with open(MEM_FILE, "w", encoding="utf-8") as f:
        json.dump(mem, f, indent=2)


def fingerprint(text):
    norm = " ".join(str(text).split())[:2000]
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()[:12]


def cmd_init(a):
    mem = load()
    save(mem)
    print(f"avo memory ready at {os.path.abspath(MEM_FILE)}")


def cmd_log(a):
    mem = load()
    fp = fingerprint(a.output)
    mem["attempts"].append({
        "ts": int(time.time()),
        "task": a.task,
        "action": a.action,
        "output_excerpt": " ".join(a.output.split())[:500],
        "fingerprint": fp,
        "status": a.status,
    })
    if a.status == "fail":
        if fp not in [p["fingerprint"] for p in mem.get("failed_patterns", [])]:
            mem.setdefault("failed_patterns", []).append({
                "fingerprint": fp,
                "note": a.action[:200],
                "ts": int(time.time())
            })
    else:
        mem["forced_continuations"] = 0
    save(mem)
    print(f"logged attempt #{len(mem['attempts'])} [{a.status}] fp={fp}")


def _stagnant(mem):
    fails = [x for x in mem.get("attempts", []) if x.get("status") == "fail"]
    recent = fails[-STAGNATION_THRESHOLD:]
    return (
        len(recent) == STAGNATION_THRESHOLD
        and len({x.get("fingerprint") for x in recent}) == 1
    )


def cmd_check(a):
    mem = load()
    if _stagnant(mem):
        print("STAGNATION: same failure fingerprint 3x in a row. "
              "Pivot strategy; consult the avo_supervisor agent.")
        sys.exit(1)
    if not getattr(a, "quiet", False):
        print("OK: no stagnation detected.")
    sys.exit(0)


def cmd_summary(a):
    mem = load()
    print(f"=== AVO Memory Summary ===")
    print(f"attempts={len(mem.get('attempts', []))} | failed_patterns={len(mem.get('failed_patterns', []))} | facts={len(mem.get('facts', []))}\n")
    if mem.get("attempts"):
        print("Recent Attempts:")
        for x in mem["attempts"][-5:]:
            print(f"  - [{x.get('status','?').upper()}] {x.get('task','')} :: {x.get('action','')} (fp={x.get('fingerprint','')})")
    if mem.get("failed_patterns"):
        print("\nKnown Dead Ends (DO NOT REPEAT):")
        for p in mem["failed_patterns"][-5:]:
            print(f"  * fp={p.get('fingerprint','')} :: {p.get('note','')}")
    if mem.get("facts"):
        print("\nVerified Facts:")
        for fct in mem["facts"][-5:]:
            print(f"  * {fct}")


def cmd_fact(a):
    mem = load()
    mem.setdefault("facts", [])
    if a.text not in mem["facts"]:
        mem["facts"].append(a.text)
    save(mem)
    print("fact stored successfully")


def cmd_status(a):
    mem = load()
    fails = sum(1 for x in mem.get("attempts", []) if x.get("status") == "fail")
    print(json.dumps({
        "version": VERSION,
        "memory_file": os.path.abspath(MEM_FILE),
        "attempts": len(mem.get("attempts", [])),
        "failures": fails,
        "failed_patterns": len(mem.get("failed_patterns", [])),
        "facts": len(mem.get("facts", [])),
        "stagnant": _stagnant(mem),
    }, indent=2))


def cmd_hook_post(a):
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return
    command = (payload.get("tool_input") or {}).get("command", "")
    if ".avo" in command or "avo " in command or "avo.py" in command:
        return
    response = json.dumps(payload.get("tool_response", ""))[:2000]
    if any(sig in response for sig in FAIL_SIGNALS):
        mem = load()
        fp = fingerprint(response)
        mem["attempts"].append({
            "ts": int(time.time()),
            "task": "(auto-hook)",
            "action": command[:200],
            "output_excerpt": " ".join(response.split())[:500],
            "fingerprint": fp,
            "status": "fail",
        })
        if fp not in [p["fingerprint"] for p in mem.get("failed_patterns", [])]:
            mem.setdefault("failed_patterns", []).append({
                "fingerprint": fp,
                "note": command[:200],
                "ts": int(time.time())
            })
        save(mem)


def cmd_hook_stop(a):
    mem = load()
    if _stagnant(mem) and mem.get("forced_continuations", 0) < MAX_FORCED_CONTINUATIONS:
        mem["forced_continuations"] = mem.get("forced_continuations", 0) + 1
        save(mem)
        sys.stderr.write("AVO supervisor: pivot required.\n")
        sys.exit(2)
    sys.exit(0)


def cmd_install(a):
    target = a.target
    dest_dir = os.path.abspath(a.path) if hasattr(a, "path") and a.path else os.getcwd()
    is_global = getattr(a, "global_install", False)
    global_rules = getattr(a, "global_rules", False)

    print(f"[AVO Plugin Installer v{VERSION}] Target: {target} (global={is_global})")

    # Global installation into ~/.gemini/config
    if is_global or (target == "antigravity" and is_global):
        home_config = os.path.expanduser("~/.gemini/config")
        agents_dir = os.path.join(home_config, "agents")
        rules_dir = os.path.join(home_config, "rules")
        
        # Global Agents
        for agent_name, template in [("avo_worker", AVO_WORKER_AGENT_MD), ("avo_supervisor", AVO_SUPERVISOR_AGENT_MD)]:
            agent_path = os.path.join(agents_dir, agent_name)
            os.makedirs(agent_path, exist_ok=True)
            with open(os.path.join(agent_path, "agent.md"), "w", encoding="utf-8") as f:
                f.write(template)
            print(f"  + Global Agent: {os.path.join(agent_path, 'agent.md')}")

        # Global Rule
        os.makedirs(rules_dir, exist_ok=True)
        global_rule_path = os.path.join(rules_dir, "avo-global.md")
        with open(global_rule_path, "w", encoding="utf-8") as f:
            f.write(AGENTS_MD_TEMPLATE)
        print(f"  + Global Rule : {global_rule_path}")
        print("[AVO Installer] Global Antigravity setup complete!")
        return

    # Local Project installation
    print(f"  Target directory: {dest_dir}")

    # 1. Memory file
    mem_path = os.path.join(dest_dir, MEM_FILE)
    if not os.path.exists(mem_path):
        with open(mem_path, "w", encoding="utf-8") as f:
            json.dump({"attempts": [], "failed_patterns": [], "facts": [], "forced_continuations": 0}, f, indent=2)
        print(f"  + Created {MEM_FILE}")

    # 2. AGENTS.md
    if target in ("all", "agents", "antigravity", "claude"):
        agents_path = os.path.join(dest_dir, "AGENTS.md")
        with open(agents_path, "w", encoding="utf-8") as f:
            f.write(AGENTS_MD_TEMPLATE)
        print(f"  + Configured AGENTS.md")

    # 3. GEMINI.md & Antigravity agents/rules
    if target in ("all", "antigravity"):
        gemini_path = os.path.join(dest_dir, "GEMINI.md")
        with open(gemini_path, "w", encoding="utf-8") as f:
            f.write(GEMINI_MD_TEMPLATE)
        print(f"  + Configured GEMINI.md (Antigravity)")

        # Local .agents/agents/
        for agent_name, template in [("avo_worker", AVO_WORKER_AGENT_MD), ("avo_supervisor", AVO_SUPERVISOR_AGENT_MD)]:
            agent_path = os.path.join(dest_dir, ".agents", "agents", agent_name)
            os.makedirs(agent_path, exist_ok=True)
            with open(os.path.join(agent_path, "agent.md"), "w", encoding="utf-8") as f:
                f.write(template)
        print(f"  + Configured .agents/agents/ (avo_worker, avo_supervisor)")

        # Local .agents/rules/
        rules_dir = os.path.join(dest_dir, ".agents", "rules")
        os.makedirs(rules_dir, exist_ok=True)
        with open(os.path.join(rules_dir, "avo.md"), "w", encoding="utf-8") as f:
            f.write(GEMINI_MD_TEMPLATE)
        print(f"  + Configured .agents/rules/avo.md")

    # 4. CLAUDE.md & .agentrules for Claude Code
    if target in ("all", "claude"):
        claude_path = os.path.join(dest_dir, "CLAUDE.md")
        if os.path.exists(claude_path):
            with open(claude_path, "r", encoding="utf-8") as f:
                content = f.read()
            if "AVO" not in content:
                with open(claude_path, "a", encoding="utf-8") as f:
                    f.write("\n\n" + CLAUDE_MD_TEMPLATE)
                print(f"  + Appended AVO block to existing CLAUDE.md")
        else:
            with open(claude_path, "w", encoding="utf-8") as f:
                f.write(CLAUDE_MD_TEMPLATE)
            print(f"  + Created CLAUDE.md")

        agentrules_path = os.path.join(dest_dir, ".agentrules")
        with open(agentrules_path, "w", encoding="utf-8") as f:
            f.write(AGENTS_MD_TEMPLATE)
        print(f"  + Configured .agentrules")

    # 5. Copy engine executables
    src_avo = os.path.abspath(__file__)
    
    # Copy to .avo/avo.py
    avo_dir = os.path.join(dest_dir, ".avo")
    os.makedirs(avo_dir, exist_ok=True)
    dest_dot_avo = os.path.join(avo_dir, "avo.py")
    try:
        if os.path.normcase(os.path.abspath(dest_dot_avo)) != os.path.normcase(src_avo):
            shutil.copy2(src_avo, dest_dot_avo)
            print(f"  + Installed .avo/avo.py")
    except Exception:
        pass

    # Copy to avo.py
    dest_avo = os.path.join(dest_dir, "avo.py")
    try:
        if os.path.exists(dest_avo) and os.path.samefile(src_avo, dest_avo):
            pass
        elif os.path.normcase(os.path.abspath(dest_avo)) != os.path.normcase(src_avo):
            shutil.copy2(src_avo, dest_avo)
            print(f"  + Installed avo.py")
    except Exception:
        pass

    if global_rules:
        home_rules = os.path.expanduser("~/.gemini/config/rules")
        os.makedirs(home_rules, exist_ok=True)
        global_rule_path = os.path.join(home_rules, "avo-global.md")
        with open(global_rule_path, "w", encoding="utf-8") as f:
            f.write(AGENTS_MD_TEMPLATE)
        print(f"  + Wrote global rules: {global_rule_path}")

    print("[AVO Installer] Complete! NVIDIA AVO Plugin active for this project.")


def cmd_doctor(a):
    print("=== NVIDIA AVO Diagnostic Check ===")
    print(f"Engine Version  : {VERSION}")
    print(f"Python Runtime  : {sys.version.split()[0]}")
    print(f"Working Directory: {os.getcwd()}")
    mem_exists = os.path.exists(MEM_FILE)
    print(f"Memory File ({MEM_FILE}): {'Found' if mem_exists else 'Not Initialized (run `python avo.py init`)'}")
    if mem_exists:
        mem = load()
        print(f"  - Total Attempts: {len(mem.get('attempts', []))}")
        print(f"  - Dead Ends     : {len(mem.get('failed_patterns', []))}")
        print(f"  - Facts Stored  : {len(mem.get('facts', []))}")
        print(f"  - Stagnant State: {_stagnant(mem)}")
    agents_exists = os.path.exists("AGENTS.md")
    gemini_exists = os.path.exists("GEMINI.md")
    claude_exists = os.path.exists("CLAUDE.md")
    dot_avo_exists = os.path.exists(os.path.join(".avo", "avo.py")) or os.path.exists("avo.py")
    print(f"AGENTS.md       : {'Found' if agents_exists else 'Missing'}")
    print(f"GEMINI.md       : {'Found' if gemini_exists else 'Missing'}")
    print(f"CLAUDE.md       : {'Found' if claude_exists else 'Missing'}")
    print(f"AVO Engine      : {'Found' if dot_avo_exists else 'Missing'}")
    
    # Global check
    g_worker = os.path.expanduser("~/.gemini/config/agents/avo_worker/agent.md")
    g_super = os.path.expanduser("~/.gemini/config/agents/avo_supervisor/agent.md")
    g_rules = os.path.expanduser("~/.gemini/config/rules/avo-global.md")
    print(f"Global Worker   : {'Found' if os.path.exists(g_worker) else 'Not installed (run with --global)'}")
    print(f"Global Super    : {'Found' if os.path.exists(g_super) else 'Not installed (run with --global)'}")
    print(f"Global Rules    : {'Found' if os.path.exists(g_rules) else 'Not installed (run with --global-rules)'}")
    print("====================================")


def main():
    p = argparse.ArgumentParser(prog="avo", description="NVIDIA AVO (Autonomous Validation Orchestrator) Engine & Plugin")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("init", help="Initialize memory file")

    lg = sub.add_parser("log", help="Log an execution attempt")
    lg.add_argument("--task", required=True)
    lg.add_argument("--action", required=True)
    lg.add_argument("--output", required=True)
    lg.add_argument("--status", choices=["success", "fail"], required=True)

    ck = sub.add_parser("check", help="Check for stagnation loop")
    ck.add_argument("--quiet", action="store_true")

    sub.add_parser("summary", help="Print memory summary")

    fa = sub.add_parser("fact", help="Record a persistent fact")
    fa.add_argument("text")

    sub.add_parser("status", help="Print JSON status of AVO engine")
    sub.add_parser("hook-post", help="Post-tool execution hook handler")
    sub.add_parser("hook-stop", help="Stop hook handler")

    ins = sub.add_parser("install", help="Install AVO plugin configuration into a directory or globally")
    ins.add_argument("--target", choices=["all", "antigravity", "claude", "agents"], default="all")
    ins.add_argument("--path", default=".")
    ins.add_argument("--global", dest="global_install", action="store_true", help="Install globally to ~/.gemini/config")
    ins.add_argument("--global-rules", action="store_true", help="Also write global rules file for Antigravity")

    sub.add_parser("doctor", help="Run system diagnostics")

    a = p.parse_args()
    handlers = {
        "init": cmd_init,
        "log": cmd_log,
        "check": cmd_check,
        "summary": cmd_summary,
        "fact": cmd_fact,
        "status": cmd_status,
        "hook-post": cmd_hook_post,
        "hook-stop": cmd_hook_stop,
        "install": cmd_install,
        "doctor": cmd_doctor
    }
    handlers[a.cmd](a)


if __name__ == "__main__":
    main()

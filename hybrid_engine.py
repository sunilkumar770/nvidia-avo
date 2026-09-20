#!/usr/bin/env python3
"""
AVO + DSH (DeepSeek Harness) Hybrid Execution Engine (v1.3.0)

Architecture:
- Macro Layer (NVIDIA AVO): Supervisor & State Optimizer. Monitors long-term memory,
  fingerprints error signatures, detects 3x stagnation loops, and injects intervention directives.
- Micro Layer (DeepSeek Harness / DSH): Granular tool execution runtime for sub-agents,
  file modifications, and command execution.
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

MEM_FILE = ".agent_memory.json"
STAGNATION_THRESHOLD = 3


class HybridAVODSHEngine:
    def __init__(self, workspace_path: str = None):
        self.workspace_path = os.path.abspath(workspace_path or os.getcwd())
        self.memory_file = os.path.join(self.workspace_path, MEM_FILE)
        self.memory = self._load_memory()

    def _load_memory(self) -> dict:
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "attempts": [],
            "failed_patterns": [],
            "facts": [],
            "sessions": [],
            "stagnation_count": 0,
            "failed_approaches": []
        }

    def _save_memory(self):
        with open(self.memory_file, 'w', encoding='utf-8') as f:
            json.dump(self.memory, f, indent=2)

    def avo_supervisor_check(self) -> bool:
        """AVO Supervisory Logic: Detects repetitive failing cycles across sessions."""
        sessions = self.memory.get("sessions", [])
        if len(sessions) >= STAGNATION_THRESHOLD:
            last_three = [s.get("output", "")[:300] for s in sessions[-STAGNATION_THRESHOLD:]]
            failures = [s for s in sessions[-STAGNATION_THRESHOLD:] if not s.get("success", False)]
            
            # Stagnation condition: 3 failures in a row with identical output snippets
            if len(failures) == STAGNATION_THRESHOLD and len(set(last_three)) == 1:
                self.memory["stagnation_count"] = self.memory.get("stagnation_count", 0) + 1
                return True
        return False

    def execute_dsh_step(self, task_prompt: str, mode: str = "standard") -> tuple[bool, str]:
        """
        DSH Execution Logic: Delegates sub-task to DeepSeek Harness CLI (or fallback native runner).
        """
        stagnant = self.avo_supervisor_check()
        
        # Inject AVO memory constraints into task prompt if repeating/stagnant
        if stagnant:
            last_failed = self.memory.get("failed_approaches", ["N/A"])[-1]
            task_prompt = (
                f"[AVO INTERVENTION: Stagnation Detected. Avoid previous failed approach: {last_failed}]. "
                f"Use a totally different architectural strategy to solve: {task_prompt}"
            )
            print("[AVO Supervisor] ⚠️  Stagnation Detected! Intervening with strategy redirect.")

        print(f"\n--- [AVO + DSH Executing Task ({mode.upper()} MODE)] ---")
        print(f"Workspace: {self.workspace_path}")
        print(f"Task     : {task_prompt[:120]}...\n")

        has_dsh_cli = shutil.which("dsh") is not None

        if has_dsh_cli:
            print("[DSH Engine] Invoking dsh CLI runner...")
            cmd = f'dsh run --mode {mode} --workspace "{self.workspace_path}" "{task_prompt}"'
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=self.workspace_path)
            output = proc.stdout + proc.stderr
            success = proc.returncode == 0
        else:
            print("[DSH Engine] `dsh` CLI not detected in PATH. Executing native runner fallback...")
            # Native fallback execution probe
            proc = subprocess.run(task_prompt, shell=True, capture_output=True, text=True, cwd=self.workspace_path)
            output = proc.stdout + proc.stderr
            success = proc.returncode == 0

        # Log session for AVO supervision
        session_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt": task_prompt,
            "mode": mode,
            "output": output[:1000],
            "success": success
        }
        self.memory.setdefault("sessions", []).append(session_entry)
        
        if not success:
            self.memory.setdefault("failed_approaches", []).append(task_prompt[:300])

        self._save_memory()
        status_str = "✅ SUCCESS" if success else "❌ FAILURE"
        print(f"[AVO + DSH Result] {status_str} (Output size: {len(output)} bytes)")
        return success, output


if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "Check system diagnostic status"
    engine = HybridAVODSHEngine(os.getcwd())
    success, result = engine.execute_dsh_step(prompt)
    print(f"\nResult Output Excerpt:\n{result[:500]}")

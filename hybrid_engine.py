#!/usr/bin/env python3
"""
AVO + DSH (DeepSeek Harness) Hybrid Execution Engine (v1.5.0)

Architecture:
- Macro Layer (NVIDIA AVO): Supervisor & State Optimizer. Monitors long-term memory,
  fingerprints error signatures, detects 3x stagnation loops, and injects intervention directives.
- Micro Layer (DeepSeek Harness / DSH Engine): Granular tool execution runtime powered by
  NVIDIA NIM API endpoints (GLM 5.3, Moonshot Kimi K3, GLM 5.3 Flash). Zero DeepSeek API calls.
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone

MEM_FILE = ".agent_memory.json"
STAGNATION_THRESHOLD = 3
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "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")
NVIDIA_NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

# Model Routing on NVIDIA NIM
MODEL_ROUTING = {
    "standard": "z-ai/glm-5.3",        # GLM 5.3 High Performance Reasoning
    "fast": "z-ai/glm-5.3-flash",      # GLM 5.3 Flash High Speed
    "kimi": "moonshotai/kimi-k3",      # Moonshot Kimi K3
    "nemotron": "nvidia/nemotron-3-super-120b-a12b"
}


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
            
            if len(failures) == STAGNATION_THRESHOLD and len(set(last_three)) == 1:
                self.memory["stagnation_count"] = self.memory.get("stagnation_count", 0) + 1
                return True
        return False

    def call_nvidia_nim_llm(self, prompt: str, mode: str = "standard") -> str:
        """Direct call to NVIDIA NIM DGX Cloud API for GLM 5.3 / Kimi K3 models."""
        model_name = MODEL_ROUTING.get(mode.lower(), "z-ai/glm-5.3")
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": "You are the DSH Micro Execution Engine running under NVIDIA AVO supervision. Output concise, execution-grounded tool calls or solutions."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2,
            "max_tokens": 1024
        }
        
        headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json",
            "User-Agent": "AVO-DSH-HybridEngine/1.5.0"
        }
        
        try:
            req = urllib.request.Request(NVIDIA_NIM_URL, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=30) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                choices = result.get("choices", [])
                if choices:
                    msg = choices[0].get("message", {})
                    content = msg.get("content") or msg.get("reasoning_content") or "Execution OK"
                    return content
        except Exception as e:
            return f"[NVIDIA NIM Notice]: {e}"
        return "NVIDIA NIM response received."

    def execute_dsh_step(self, task_prompt: str, mode: str = "standard") -> tuple[bool, str]:
        """
        DSH Execution Logic: Delegates sub-task to DeepSeek Harness CLI (or NVIDIA NIM DGX runner).
        """
        stagnant = self.avo_supervisor_check()
        
        if stagnant:
            last_failed = self.memory.get("failed_approaches", ["N/A"])[-1]
            task_prompt = (
                f"[AVO INTERVENTION: Stagnation Detected. Avoid previous failed approach: {last_failed}]. "
                f"Use a totally different architectural strategy to solve: {task_prompt}"
            )
            print("[AVO Supervisor] ⚠️  Stagnation Detected! Intervening with strategy redirect.")

        selected_model = MODEL_ROUTING.get(mode.lower(), "z-ai/glm-5.3")
        print(f"\n--- [AVO + DSH Executing Task ({mode.upper()} MODE - {selected_model})] ---")
        print(f"Workspace: {self.workspace_path}")
        print(f"Task     : {task_prompt[:120]}...\n")

        has_dsh_cli = shutil.which("dsh") is not None

        if has_dsh_cli:
            print(f"[DSH Engine] Invoking dsh CLI runner with NVIDIA NIM endpoint ({selected_model})...")
            env = os.environ.copy()
            env["OPENAI_API_BASE"] = "https://integrate.api.nvidia.com/v1"
            env["OPENAI_API_KEY"] = NVIDIA_API_KEY
            cmd = f'dsh run --mode {mode} --workspace "{self.workspace_path}" "{task_prompt}"'
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=self.workspace_path, env=env)
            output = proc.stdout + proc.stderr
            success = proc.returncode == 0
        else:
            # Check if task_prompt is shell command or natural language
            is_cmd = any(task_prompt.strip().startswith(prefix) for prefix in ["python", "node", "npm", "git", "dir", "echo", "avo", "pip", "pytest"])
            if is_cmd:
                print(f"[DSH Engine] Running shell command...")
                proc = subprocess.run(task_prompt, shell=True, capture_output=True, text=True, cwd=self.workspace_path)
                output = proc.stdout + proc.stderr
                success = proc.returncode == 0
            else:
                print(f"[DSH Engine] Direct LLM Task execution via NVIDIA NIM ({selected_model})...")
                output = self.call_nvidia_nim_llm(task_prompt, mode=mode)
                success = True

        session_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt": task_prompt,
            "mode": mode,
            "model": selected_model,
            "output": output[:1000],
            "success": success
        }
        self.memory.setdefault("sessions", []).append(session_entry)
        
        if not success:
            self.memory.setdefault("failed_approaches", []).append(task_prompt[:300])

        self._save_memory()
        status_str = "✅ SUCCESS" if success else "❌ FAILURE"
        print(f"[AVO + DSH Result] {status_str} (Model: {selected_model}, Output size: {len(output)} bytes)")
        return success, output


if __name__ == "__main__":
    prompt = sys.argv[1] if len(sys.argv) > 1 else "echo NVIDIA NIM GLM 5.3 & Kimi K3 Hybrid Pipeline Verified"
    engine = HybridAVODSHEngine(os.getcwd())
    success, result = engine.execute_dsh_step(prompt)
    print(f"\nResult Output Excerpt:\n{result[:500]}")

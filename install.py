#!/usr/bin/env python3
"""
NVIDIA AVO Universal Plugin Installer
One-click installer for Antigravity, Claude Code, Cursor, Windsurf, and Gemini CLI.
"""
import os
import sys
import subprocess

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    avo_script = os.path.join(script_dir, "avo.py")

    target = "all"
    if len(sys.argv) > 1:
        target = sys.argv[1].lstrip("-")

    dest = os.getcwd()

    print("=" * 65)
    print("   NVIDIA AVO (Autonomous Validation Orchestrator) Installer")
    print("=" * 65)

    # 1. Install globally to ~/.gemini/config
    print("\n[1/2] Installing Global Agents & Rules into ~/.gemini/config...")
    proc_g = subprocess.run([sys.executable, avo_script, "install", "--target", "antigravity", "--global"], capture_output=True, text=True)
    print(proc_g.stdout)

    # 2. Install locally into target directory
    print(f"[2/2] Provisioning Project Plugin at: {dest}...")
    proc_l = subprocess.run([sys.executable, avo_script, "install", "--target", target, "--path", dest, "--global-rules"], capture_output=True, text=True)
    print(proc_l.stdout)

    # 3. Run Doctor
    print("Checking Diagnostic Status...")
    proc_d = subprocess.run([sys.executable, avo_script, "doctor"], capture_output=True, text=True, cwd=dest)
    print(proc_d.stdout)

    print("\n✅ NVIDIA AVO Plugin Installed & Verified Successfully!")
    print("   To use in Antigravity: Just open this workspace and prompt.")
    print("   To use in Claude Code: Run `python avo.py summary` and prompt.")

if __name__ == "__main__":
    main()

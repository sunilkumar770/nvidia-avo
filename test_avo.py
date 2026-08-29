import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

PYTHON_EXE = sys.executable
AVO_SCRIPT = str(Path(__file__).parent / "avo.py")


class TestNVIDIAAVO(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(__file__).parent / "_test_avo_tmp"
        self.test_dir.mkdir(exist_ok=True)
        self.orig_cwd = os.getcwd()
        os.chdir(self.test_dir)

    def tearDown(self):
        os.chdir(self.orig_cwd)
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def run_avo(self, *args):
        cmd = [PYTHON_EXE, AVO_SCRIPT] + list(args)
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res

    def test_01_init(self):
        r = self.run_avo("init")
        self.assertEqual(r.returncode, 0)
        self.assertTrue(os.path.exists(".agent_memory.json"))

    def test_02_log_and_fact(self):
        self.run_avo("init")
        r_log = self.run_avo("log", "--task", "test task", "--action", "test action", "--output", "all good", "--status", "success")
        self.assertEqual(r_log.returncode, 0)

        r_fact = self.run_avo("fact", "Database port is 5432")
        self.assertEqual(r_fact.returncode, 0)

        with open(".agent_memory.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["attempts"]), 1)
        self.assertIn("Database port is 5432", data["facts"])

    def test_03_check_ok(self):
        self.run_avo("init")
        r = self.run_avo("check")
        self.assertEqual(r.returncode, 0)
        self.assertIn("OK", r.stdout)

    def test_04_stagnation_detection(self):
        self.run_avo("init")
        err_msg = "Error: Connection refused on port 4001"
        for _ in range(3):
            self.run_avo("log", "--task", "start bridge", "--action", "run node", "--output", err_msg, "--status", "fail")
        
        r_check = self.run_avo("check")
        self.assertEqual(r_check.returncode, 1)
        self.assertIn("STAGNATION", r_check.stdout)

    def test_05_failed_patterns_dedupe(self):
        self.run_avo("init")
        err = "FATAL: Out of memory"
        self.run_avo("log", "--task", "build", "--action", "mvn clean install", "--output", err, "--status", "fail")
        self.run_avo("log", "--task", "build retry", "--action", "mvn clean install", "--output", err, "--status", "fail")
        
        with open(".agent_memory.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(len(data["attempts"]), 2)
        self.assertEqual(len(data["failed_patterns"]), 1)

    def test_06_install_targets(self):
        r = self.run_avo("install", "--target", "antigravity", "--path", str(self.test_dir))
        self.assertEqual(r.returncode, 0)
        self.assertTrue(os.path.exists("GEMINI.md"))
        self.assertTrue(os.path.exists("AGENTS.md"))
        self.assertTrue(os.path.exists(".agents/rules/avo.md"))

    def test_07_status_json(self):
        self.run_avo("init")
        r = self.run_avo("status")
        self.assertEqual(r.returncode, 0)
        status_data = json.loads(r.stdout)
        self.assertTrue(status_data["version"].startswith("1."))
        self.assertFalse(status_data["stagnant"])


if __name__ == "__main__":
    unittest.main()

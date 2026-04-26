import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "manage_data.py"


def run(args, env_extra, stdin=None):
    env = {**os.environ, **env_extra}
    return subprocess.run(["python3", str(SCRIPT)] + args,
                          capture_output=True, text=True, env=env, input=stdin, check=False)


class SignalsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        cfg_dir = Path(self.tmp.name) / "home" / ".you-read-i-read"; cfg_dir.mkdir(parents=True)
        self.data = Path(self.tmp.name) / "data"; self.data.mkdir(parents=True)
        (cfg_dir / "config.yaml").write_text(f"data_repo:\n  path: {self.data}\n")
        self.env = {"HOME": str(Path(self.tmp.name) / "home")}

    def tearDown(self):
        self.tmp.cleanup()

    def test_signal_log_appends_and_updates_state(self):
        r = run(["signal-log", "--event", "update_accepted",
                 "--paper-id", "arxiv-2401.00001",
                 "--field", "tag=tool-use"], self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        record = json.loads(r.stdout)
        self.assertEqual(record["event"], "update_accepted")

        # signals.jsonl appended
        sig_path = self.data / "preferences" / "signals.jsonl"
        self.assertTrue(sig_path.exists())
        lines = sig_path.read_text().splitlines()
        self.assertEqual(len(lines), 1)

        # preference-state.yaml created and reflects the accept
        import yaml
        state_path = self.data / "preferences" / "preference-state.yaml"
        self.assertTrue(state_path.exists())
        state = yaml.safe_load(state_path.read_text())
        self.assertEqual(state["totals"]["signals"], 1)
        self.assertEqual(state["totals"]["accepted"], 1)
        # Schema is minimal: totals + recommended_mode + last_recomputed.
        self.assertEqual(state["recommended_mode"], "interactive")
        self.assertNotIn("recent_positives", state)
        self.assertNotIn("tags", state)

    def test_signal_log_recommends_semi_auto_after_25(self):
        for i in range(25):
            run(["signal-log", "--event", "update_accepted",
                 "--paper-id", f"arxiv-2401.{i:05d}"], self.env)
        import yaml
        state = yaml.safe_load((self.data / "preferences" / "preference-state.yaml").read_text())
        self.assertEqual(state["recommended_mode"], "semi-auto")


if __name__ == "__main__":
    unittest.main()

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "manage_data.py"


def run(args, env_extra):
    env = {**os.environ, **env_extra}
    return subprocess.run(
        ["python3", str(SCRIPT)] + args,
        capture_output=True, text=True, env=env, check=False,
    )


class PaperSubcommandsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        # Write a minimal user config that points data_repo at the tmp dir.
        user_cfg_dir = Path(self.tmp.name) / "home" / ".you-read-i-read"
        user_cfg_dir.mkdir(parents=True)
        data_dir = Path(self.tmp.name) / "data"
        data_dir.mkdir(parents=True)
        (user_cfg_dir / "config.yaml").write_text(
            f"data_repo:\n  path: {data_dir}\n"
        )
        # Force HOME so _common.USER_CONFIG_PATH resolves into the tmp config.
        self.env = {"HOME": str(Path(self.tmp.name) / "home")}

    def tearDown(self):
        self.tmp.cleanup()

    def test_paper_add_then_get(self):
        r = run(["paper-add", "--url", "https://arxiv.org/abs/2401.12345",
                 "--title", "Foo", "--via", "url"], self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        entry = json.loads(r.stdout)
        self.assertEqual(entry["id"], "arxiv-2401.12345")
        self.assertEqual(entry["status"], "to-read")

        r = run(["paper-get", "arxiv-2401.12345"], self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["title"], "Foo")

    def test_paper_list_filter_by_status(self):
        run(["paper-add", "--url", "https://arxiv.org/abs/2401.00001",
             "--title", "A", "--via", "url"], self.env)
        run(["paper-add", "--url", "https://arxiv.org/abs/2401.00002",
             "--title", "B", "--status", "read", "--via", "url"], self.env)

        r = run(["paper-list", "--status", "to-read"], self.env)
        ids = [p["id"] for p in json.loads(r.stdout)]
        self.assertIn("arxiv-2401.00001", ids)
        self.assertNotIn("arxiv-2401.00002", ids)

    def test_paper_update_status(self):
        run(["paper-add", "--url", "https://arxiv.org/abs/2401.00003",
             "--title", "C", "--via", "url"], self.env)
        r = run(["paper-update", "arxiv-2401.00003", "--status", "read"], self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["status"], "read")

    def test_paper_set_raw_via_stdin(self):
        run(["paper-add", "--url", "https://arxiv.org/abs/2401.99999",
             "--title", "Raw test", "--via", "url"], self.env)

        body = b"raw body bytes \xff\x00 with binary"
        env = {**os.environ, **self.env}
        r = subprocess.run(
            ["python3", str(SCRIPT), "paper-set-raw", "arxiv-2401.99999", "--ext", "txt"],
            input=body, capture_output=True, env=env,
        )
        self.assertEqual(r.returncode, 0, r.stderr)

        raw_path = Path(self.tmp.name) / "data" / "papers" / "raw" / "arxiv-2401.99999.txt"
        self.assertTrue(raw_path.exists(), f"raw file missing at {raw_path}")
        self.assertEqual(raw_path.read_bytes(), body)


if __name__ == "__main__":
    unittest.main()

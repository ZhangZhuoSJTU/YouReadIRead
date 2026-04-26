import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SCRIPT = REPO / "scripts" / "manage_data.py"


def run(args, env_extra):
    env = {**os.environ, **env_extra}
    return subprocess.run(["python3", str(SCRIPT)] + args,
                          capture_output=True, text=True, env=env, check=False)


class TrackingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        cfg_dir = Path(self.tmp.name) / "home" / ".you-read-i-read"
        cfg_dir.mkdir(parents=True)
        data_dir = Path(self.tmp.name) / "data"; data_dir.mkdir(parents=True)
        (cfg_dir / "config.yaml").write_text(f"data_repo:\n  path: {data_dir}\n")
        self.env = {"HOME": str(Path(self.tmp.name) / "home")}

    def tearDown(self):
        self.tmp.cleanup()

    def test_group_add_and_list(self):
        r = run(["group-add", "--display-name", "Stanford NLP",
                 "--source", "kind=semantic-scholar-author,id=1741101"], self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["id"], "stanford-nlp")

        r = run(["group-list"], self.env)
        groups = json.loads(r.stdout)["groups"]
        self.assertEqual(len(groups), 1)

    def test_topic_add_and_list(self):
        r = run(["topic-add", "--display-name", "LLM agents",
                 "--query", "source=arxiv,q=abs:LLM agents"], self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["id"], "llm-agents")

        r = run(["topic-list"], self.env)
        self.assertEqual(len(json.loads(r.stdout)["topics"]), 1)

    def test_state_set_and_get_last_checked(self):
        r = run(["state-set-last-checked", "--kind", "groups", "--id", "stanford-nlp"], self.env)
        self.assertEqual(r.returncode, 0, r.stderr)
        ts = json.loads(r.stdout)["last_checked"]
        self.assertRegex(ts, r"^\d{4}-\d{2}-\d{2}T")

        r = run(["state-get-last-checked", "--kind", "groups", "--id", "stanford-nlp"], self.env)
        self.assertEqual(json.loads(r.stdout)["last_checked"], ts)


if __name__ == "__main__":
    unittest.main()

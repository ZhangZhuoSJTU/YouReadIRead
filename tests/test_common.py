import os
import sys
import unittest
from pathlib import Path

# Make scripts/ importable.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from _common import paper_id_for, slugify, now_iso


class TestPaperIdFor(unittest.TestCase):
    def test_arxiv_abs(self):
        self.assertEqual(paper_id_for("https://arxiv.org/abs/2401.12345"), "arxiv-2401.12345")

    def test_arxiv_abs_with_version(self):
        self.assertEqual(paper_id_for("https://arxiv.org/abs/2401.12345v3"), "arxiv-2401.12345")

    def test_arxiv_pdf(self):
        self.assertEqual(paper_id_for("https://arxiv.org/pdf/2401.12345.pdf"), "arxiv-2401.12345")

    def test_doi(self):
        self.assertEqual(paper_id_for("https://doi.org/10.1145/3576915.3623123"),
                         "doi-10.1145-3576915.3623123")

    def test_generic_url_is_deterministic(self):
        # Determinism: same URL → same SHA1-based slug across runs.
        # The exact hash below is precomputed once and asserted to catch
        # accidental changes to the hashing scheme.
        url = "https://example.com/foo/bar"
        self.assertEqual(paper_id_for(url), "url-1132614ad856")


class TestSlugify(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(slugify("Stanford NLP Group"), "stanford-nlp-group")

    def test_punctuation_collapsed(self):
        self.assertEqual(slugify("LLM agents!! tool/use"), "llm-agents-tool-use")

    def test_empty_returns_item(self):
        self.assertEqual(slugify(""), "item")


class TestNowIso(unittest.TestCase):
    def test_format(self):
        ts = now_iso()
        # 2026-04-26T10:32:00Z
        self.assertRegex(ts, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


if __name__ == "__main__":
    unittest.main()

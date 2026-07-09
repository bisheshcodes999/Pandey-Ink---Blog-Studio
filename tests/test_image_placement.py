"""Unit tests for backend/reducer/image_placement.py.

Pure string logic, zero heavy deps (no LangChain/diffusers/Ollama), so
this runs anywhere with just the stdlib -- no venv, no model, no API
keys needed:

    python -m unittest tests.test_image_placement -v

or, if pytest is installed:

    pytest tests/test_image_placement.py -v
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Run directly (python tests/test_image_placement.py) or as a module
# (python -m unittest ...) without needing the package installed.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.reducer.image_placement import (
    failed_image_block,
    heading_pattern,
    insert_after_heading,
    safe_slug,
)


class SafeSlugTests(unittest.TestCase):
    def test_basic_title(self):
        self.assertEqual(safe_slug("How CPUs Work"), "how_cpus_work")

    def test_strips_punctuation(self):
        self.assertEqual(safe_slug("What Is TLS?! (Explained)"), "what_is_tls_explained")

    def test_collapses_whitespace(self):
        self.assertEqual(safe_slug("  Too   Many    Spaces  "), "too_many_spaces")

    def test_empty_title_falls_back(self):
        self.assertEqual(safe_slug(""), "blog")

    def test_only_punctuation_falls_back(self):
        self.assertEqual(safe_slug("???!!!"), "blog")


class HeadingPatternTests(unittest.TestCase):
    def test_matches_exact_heading(self):
        md = "# Title\n\n## Fetch, Decode, Execute\n\nBody text.\n"
        self.assertIsNotNone(heading_pattern("Fetch, Decode, Execute").search(md))

    def test_does_not_match_substring_of_a_longer_heading(self):
        md = "## Fetch, Decode, Execute, And Then Some\n\nBody.\n"
        self.assertIsNone(heading_pattern("Fetch, Decode, Execute").search(md))

    def test_tolerant_of_trailing_punctuation_and_case(self):
        md = "## fetch, decode, execute:\n\nBody.\n"
        self.assertIsNotNone(heading_pattern("Fetch, Decode, Execute").search(md))


class InsertAfterHeadingTests(unittest.TestCase):
    def test_inserts_right_under_matching_heading(self):
        md = "# Title\n\n## Intro\n\nIntro body.\n\n## Details\n\nDetails body.\n"
        result = insert_after_heading(md, "Intro", "![img](images/x.png)")

        intro_pos = result.index("## Intro")
        image_pos = result.index("![img](images/x.png)")
        details_pos = result.index("## Details")
        # image must land between the Intro heading and the Details
        # heading, not before Intro and not after Details.
        self.assertTrue(intro_pos < image_pos < details_pos)

    def test_does_not_disturb_other_sections(self):
        md = "## A\n\nBody A.\n\n## B\n\nBody B.\n"
        result = insert_after_heading(md, "A", "IMG_A")
        self.assertIn("Body A.", result)
        self.assertIn("Body B.", result)
        self.assertIn("IMG_A", result)

    def test_falls_back_to_appending_when_heading_not_found(self):
        md = "## Only Section\n\nBody.\n"
        result = insert_after_heading(md, "Nonexistent Section", "IMG_MISSING")
        self.assertTrue(result.rstrip().endswith("IMG_MISSING"))

    def test_on_miss_callback_fires_only_on_fallback(self):
        misses = []
        md = "## Real Section\n\nBody.\n"

        insert_after_heading(md, "Real Section", "IMG", on_miss=misses.append)
        self.assertEqual(misses, [])

        insert_after_heading(md, "Fake Section", "IMG", on_miss=misses.append)
        self.assertEqual(misses, ["Fake Section"])


class FailedImageBlockTests(unittest.TestCase):
    def test_contains_all_fields(self):
        spec = {"caption": "A diagram", "alt": "diagram alt text", "prompt": "draw a diagram"}
        block = failed_image_block(spec, "connection timed out")

        self.assertIn("[IMAGE GENERATION FAILED]", block)
        self.assertIn("A diagram", block)
        self.assertIn("diagram alt text", block)
        self.assertIn("draw a diagram", block)
        self.assertIn("connection timed out", block)

    def test_missing_optional_fields_dont_crash(self):
        block = failed_image_block({}, "some error")
        self.assertIn("[IMAGE GENERATION FAILED]", block)
        self.assertIn("some error", block)


if __name__ == "__main__":
    unittest.main()

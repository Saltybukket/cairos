import json
import tempfile
import unittest
from pathlib import Path

from cairos.router_dataset import dataset_stats, load_rows


class RouterDatasetTests(unittest.TestCase):
    def test_stats_handle_invalid_missing_and_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "router.jsonl"
            rows = [
                {"text": "create folder docs", "label": "template", "template_category": "files", "shell_hint": "posix", "risk_hint": "low"},
                {"text": "create folder docs", "label": "template"},
                {"text": "hello", "label": "conversation"},
                {"text": "missing label"},
            ]
            path.write_text("\n".join(json.dumps(row) for row in rows) + "\n{broken\n", encoding="utf-8")
            stats = dataset_stats(path)
            self.assertEqual(stats.rows, 4)
            self.assertEqual(stats.invalid_json_lines, 1)
            self.assertEqual(stats.missing_field_count, 1)
            self.assertEqual(stats.duplicate_text_count, 1)
            self.assertEqual(stats.label_distribution["template"], 2)
            loaded = load_rows(path)
            self.assertEqual(len(loaded), 3)


if __name__ == "__main__":
    unittest.main()

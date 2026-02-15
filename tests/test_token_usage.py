"""Unit tests for persistent token usage storage."""

from __future__ import annotations

import unittest
import uuid
from pathlib import Path
import shutil
from unittest.mock import patch

from core import token_usage


class TokenUsageTests(unittest.TestCase):
    def _make_local_tmp_dir(self) -> Path:
        root = Path.cwd() / ".tmp_token_usage_tests"
        root.mkdir(parents=True, exist_ok=True)
        path = root / f"run_{uuid.uuid4().hex}"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def test_record_and_snapshot_accumulate_by_provider(self) -> None:
        tmpdir = self._make_local_tmp_dir()
        try:
            with patch(
                "core.token_usage._resolve_storage_dir",
                return_value=tmpdir,
            ):
                token_usage.reset_token_usage()
                token_usage.record_token_usage("gemini", 120, 45)
                token_usage.record_token_usage("mistral", 30, 10, request_count=2)

                snapshot = token_usage.get_token_usage_snapshot()
                self.assertEqual(snapshot["providers"]["gemini"]["input_tokens"], 120)
                self.assertEqual(snapshot["providers"]["gemini"]["output_tokens"], 45)
                self.assertEqual(snapshot["providers"]["gemini"]["requests"], 1)
                self.assertEqual(snapshot["providers"]["mistral"]["input_tokens"], 30)
                self.assertEqual(snapshot["providers"]["mistral"]["output_tokens"], 10)
                self.assertEqual(snapshot["providers"]["mistral"]["requests"], 2)
                self.assertEqual(snapshot["totals"]["input_tokens"], 150)
                self.assertEqual(snapshot["totals"]["output_tokens"], 55)
                self.assertEqual(snapshot["totals"]["requests"], 3)
                self.assertTrue(token_usage.token_usage_file_path().exists())
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_backup_files_are_created_without_overwriting(self) -> None:
        tmpdir = self._make_local_tmp_dir()
        try:
            with patch(
                "core.token_usage._resolve_storage_dir",
                return_value=tmpdir,
            ):
                token_usage.reset_token_usage()
                token_usage.record_token_usage("gemini", 1, 1)
                backup_dir = token_usage.token_usage_backup_dir_path()
                backups_after_first = sorted(backup_dir.glob("*.json"))
                self.assertGreaterEqual(len(backups_after_first), 1)
                existing_names = {path.name for path in backups_after_first}

                token_usage.record_token_usage("gemini", 2, 2)
                backups_after_second = sorted(backup_dir.glob("*.json"))
                self.assertGreater(len(backups_after_second), len(backups_after_first))
                self.assertTrue(existing_names.issubset({path.name for path in backups_after_second}))
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()

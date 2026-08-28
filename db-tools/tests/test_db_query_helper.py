import contextlib
import importlib.util
import io
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "db_query_helper.py"
SPEC = importlib.util.spec_from_file_location("db_query_helper", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


SAMPLE_DATA = {
    "env": "local",
    "executed_at": "2026-08-28 12:00:00",
    "elapsed_seconds": 0.125,
    "row_count": 1,
    "sql": "SELECT id, created_at FROM sample LIMIT 1",
    "columns": ["id", "created_at"],
    "rows": [[1, datetime(2026, 8, 28, 12, 0, 0)]],
}


class CliLoggingTests(unittest.TestCase):
    def run_main(self, output_format):
        stdout = io.StringIO()
        arguments = [
            str(SCRIPT),
            "--env",
            "local",
            "--sql",
            SAMPLE_DATA["sql"],
            "--format",
            output_format,
        ]
        with (
            mock.patch.object(sys, "argv", arguments),
            mock.patch.object(MODULE, "run_query", return_value=SAMPLE_DATA),
            contextlib.redirect_stdout(stdout),
        ):
            MODULE.main()
        return stdout.getvalue()

    def test_json_logging_preserves_machine_readable_stdout(self):
        output = self.run_main("json")
        self.assertEqual(output, MODULE.format_json(SAMPLE_DATA) + "\n")
        self.assertNotIn("[INFO]", output)

    def test_markdown_logging_preserves_cli_stdout(self):
        output = self.run_main("markdown")
        self.assertEqual(output, MODULE.format_markdown(SAMPLE_DATA) + "\n")
        self.assertNotIn("[INFO]", output)


if __name__ == "__main__":
    unittest.main()

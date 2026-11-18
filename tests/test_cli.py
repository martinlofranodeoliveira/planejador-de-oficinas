"""CLI real e limites de transporte, independentes do conteúdo do núcleo."""
import contextlib
import importlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from planejador_oficinas import InputError

cli = importlib.import_module("planejador_oficinas.__main__")
ROOT = Path(__file__).resolve().parents[1]


class PublicCliTests(unittest.TestCase):
    def run_bytes(self, data, *extra):
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "SENTINEL_PRIVATE.json"
            filename.write_bytes(data)
            return subprocess.run([sys.executable, "-B", "-m", "planejador_oficinas", str(filename), *extra],
                                  capture_output=True, timeout=15, cwd=ROOT)

    def assert_error(self, result):
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(result.stderr, b"INVALID_INPUT\n")

    def test_help_does_not_open_file(self):
        output = io.StringIO()
        with patch("builtins.open", side_effect=AssertionError("help read input")), contextlib.redirect_stdout(output):
            self.assertEqual(cli.main(["--help"]), 0)
        self.assertEqual(output.getvalue(), cli.USAGE)

    def test_invalid_utf8_duplicate_keys_nonfinite_and_trailing_json(self):
        for data in (b"\xff", b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}',
                     b'{"x":1e9999}', b"{} {}", b"\xef\xbb\xbf{}"):
            with self.subTest(data=data):
                self.assert_error(self.run_bytes(data))

    def test_file_byte_bound_is_inclusive_and_checked_before_core(self):
        for length, should_call in ((1048576, True), (1048577, False)):
            raw = b"{}" + b" " * (length - 2)
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "input.json"
                path.write_bytes(raw)
                result = {"status": "scheduled", "assignments": [], "stats": {"nodes": 0, "limit": 20000}}
                with patch.object(cli, "plan", return_value=result) as call, contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    code = cli.main([str(path)])
                self.assertEqual(call.called, should_call)
                self.assertEqual(code, 0 if should_call else 2)

    def test_safe_file_and_argument_errors(self):
        result = subprocess.run([sys.executable, "-B", "-m", "planejador_oficinas", "/missing/SENTINEL_PRIVATE"],
                                capture_output=True, timeout=15, cwd=ROOT)
        self.assert_error(result)
        for argv in ([], ["file", "--other", "1"], ["file", "--max-nodes", "01"],
                     ["file", "--max-nodes", "200001"], ["file", "--max-nodes", "１"]):
            with self.subTest(argv=argv), patch("builtins.open", side_effect=AssertionError("bad args read input")), contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as error:
                self.assertEqual(cli.main(argv), 2)
                self.assertEqual(out.getvalue(), "")
                self.assertEqual(error.getvalue(), "INVALID_INPUT\n")

    def test_static_cli_exits_and_safe_core_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.json"
            path.write_text("{}", encoding="utf-8")
            for status, expected in (("scheduled", 0), ("unsatisfiable", 1), ("budget_exhausted", 3)):
                result = {"status": status, "assignments": [], "stats": {"nodes": 1, "limit": 7}}
                with patch.object(cli, "plan", return_value=result) as call, contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as error:
                    self.assertEqual(cli.main([str(path), "--max-nodes", "7"]), expected)
                    call.assert_called_once_with({}, max_nodes=7)
                    self.assertEqual(json.loads(out.getvalue()), result)
                    self.assertEqual(error.getvalue(), "")
            with patch.object(cli, "plan", side_effect=InputError("SENTINEL_PRIVATE")), contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()) as error:
                self.assertEqual(cli.main([str(path)]), 2)
                self.assertEqual(out.getvalue(), "")
                self.assertEqual(error.getvalue(), "INVALID_INPUT\n")

    def test_real_feasible_example(self):
        result = self.run_bytes((ROOT / "examples/viavel.json").read_bytes())
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stderr, b"")
        self.assertEqual(json.loads(result.stdout)["status"], "scheduled")

    def test_real_impossible_example(self):
        result = self.run_bytes((ROOT / "examples/inviavel.json").read_bytes())
        self.assertEqual(result.returncode, 1)
        self.assertEqual(json.loads(result.stdout)["status"], "unsatisfiable")

    def test_real_budget_exhaustion_example(self):
        result = self.run_bytes((ROOT / "examples/busca-limitada.json").read_bytes(), "--max-nodes", "1")
        self.assertEqual(result.returncode, 3)
        self.assertEqual(json.loads(result.stdout)["status"], "budget_exhausted")


if __name__ == "__main__":
    unittest.main()

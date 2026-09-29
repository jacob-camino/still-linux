"""Exercise the pre-upload budget guard with sparse temporary inputs."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "check-artifact-size.py"


class ArtifactSizeTest(unittest.TestCase):
    def check_sizes(self, sizes):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for index, size in enumerate(sizes):
                path = Path(directory) / str(index)
                with path.open("wb") as file:
                    file.truncate(size)
                paths.append(str(path))
            return subprocess.run(
                [sys.executable, str(SCRIPT), "--max-gib", "1", *paths],
                capture_output=True, text=True,
            )

    def test_small_artifact_is_allowed(self):
        self.assertEqual(self.check_sizes([1]).returncode, 0)

    def test_empty_and_missing_artifacts_are_rejected(self):
        self.assertNotEqual(self.check_sizes([0]).returncode, 0)
        self.assertNotEqual(self.check_sizes([]).returncode, 0)

    def test_single_oversized_artifact_is_rejected(self):
        result = self.check_sizes([1024 ** 3 + 1])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("exceeds", result.stderr)

    def test_combined_package_size_is_bounded(self):
        self.assertEqual(self.check_sizes([512 * 1024 ** 2] * 2).returncode, 0)
        self.assertNotEqual(self.check_sizes([600 * 1024 ** 2] * 2).returncode, 0)

#!/usr/bin/env python3

import unittest
from pathlib import Path

from refrepo_git import inject_reference_repo_arg

# Test inject_reference_repo_arg
class InjectReferenceRepoArg(unittest.TestCase):
    def setUp(self):
        # These are needed for inject_reference_repo_arg, so set them to
        # something we can be sure exists.
        self.root = Path("/usr")
        self.refrepo = Path("bin")
        self.refrepo_full = self.root / self.refrepo

    def test_simple_clone(self):
        args = ["clone"]
        expected = ["clone", "--reference", f"{self.refrepo_full}"]
        actual = inject_reference_repo_arg(args, self.root, self.refrepo)

        self.assertEqual(expected, actual)

    def test_simple_submodule(self):
        args = [
            "submodule",
            "update",
            "--init",
            "--recursive",
        ]
        expected = [
            "submodule",
            "update",
            "--reference",
            f"{self.refrepo_full}",
            "--init",
            "--recursive",
        ]
        actual = inject_reference_repo_arg(args, self.root, self.refrepo)

        self.assertEqual(expected, actual)

    # Test that we handle arguments between git and the subcommand correctly.
    def test_pre_command_args(self):
        args = [
            "-C",
            "/tmp/test-repo",
            "submodule",
            "update",
            "--init",
            "--recursive",
        ]
        expected = [
            "-C",
            "/tmp/test-repo",
            "submodule",
            "update",
            "--reference",
            f"{self.refrepo_full}",
            "--init",
            "--recursive",
        ]
        actual = inject_reference_repo_arg(args, self.root, self.refrepo)

        self.assertEqual(expected, actual)


if __name__ == "__main__":
    unittest.main()

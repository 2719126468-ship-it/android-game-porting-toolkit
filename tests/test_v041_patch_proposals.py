from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agpt.core.patches import PatchProposalError, create_patch_proposal


class PatchProposalTests(unittest.TestCase):
    def test_creates_review_only_diff_without_modifying_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "game"
            project = root / "project"
            source.mkdir()
            project.mkdir()
            target = source / "main.c"
            original = "int main(void) { return 0; }\n"
            target.write_text(original, encoding="utf-8")
            result = create_patch_proposal(
                source, project,
                file_path="main.c",
                replacement_text="int main(void) { return 1; }\n",
                rationale="Return a non-zero exit code for the failure path.",
                evidence=["test: failure exit path"],
            )
            data = json.loads(Path(result["proposal_path"]).read_text(encoding="utf-8"))
            self.assertIn("-int main(void) { return 0; }", data["unified_diff"])
            self.assertIn("+int main(void) { return 1; }", data["unified_diff"])
            self.assertTrue(data["approval_required"])
            self.assertFalse(data["applied"])
            self.assertFalse(data["safety"]["source_tree_modified"])
            self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_rejects_parent_traversal_and_absolute_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "game"
            source.mkdir()
            (source / "x.txt").write_text("old\n")
            for unsafe in ("../outside.txt", "/etc/passwd", r"..\\outside.txt"):
                with self.subTest(path=unsafe):
                    with self.assertRaises(PatchProposalError):
                        create_patch_proposal(
                            source, root / "project", file_path=unsafe,
                            replacement_text="new\n", rationale="unsafe path test",
                        )

    def test_rejects_symbolic_link_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "game"
            source.mkdir()
            outside = root / "outside.txt"
            outside.write_text("do not touch\n")
            link = source / "link.txt"
            try:
                link.symlink_to(outside)
            except (OSError, NotImplementedError):
                self.skipTest("symbolic links are unavailable on this host")
            with self.assertRaises(PatchProposalError):
                create_patch_proposal(
                    source, root / "project", file_path="link.txt",
                    replacement_text="changed\n", rationale="symlink test",
                )
            self.assertEqual(outside.read_text(), "do not touch\n")

    def test_rejects_binary_invalid_utf8_and_oversized_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "game"
            source.mkdir()
            binary = source / "binary.dat"
            binary.write_bytes(b"abc\x00def")
            with self.assertRaises(PatchProposalError):
                create_patch_proposal(
                    source, root / "project", file_path="binary.dat",
                    replacement_text="text", rationale="binary test",
                )
            invalid = source / "invalid.txt"
            invalid.write_bytes(b"\xff\xfe")
            with self.assertRaises(PatchProposalError):
                create_patch_proposal(
                    source, root / "project", file_path="invalid.txt",
                    replacement_text="text", rationale="encoding test",
                )
            large = source / "large.txt"
            large.write_bytes(b"x" * (1024 * 1024 + 1))
            with self.assertRaises(PatchProposalError):
                create_patch_proposal(
                    source, root / "project", file_path="large.txt",
                    replacement_text="text", rationale="size test",
                )

    def test_rejects_empty_rationale_and_noop_replacements(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "game"
            source.mkdir()
            (source / "main.c").write_bytes(b"same\r\n")
            with self.assertRaises(PatchProposalError):
                create_patch_proposal(
                    source, root / "project", file_path="main.c",
                    replacement_text="other\n", rationale=" ",
                )
            with self.assertRaises(PatchProposalError):
                create_patch_proposal(
                    source, root / "project", file_path="main.c",
                    replacement_text="same\n", rationale="no-op",
                )


if __name__ == "__main__":
    unittest.main()

"""Portable checks for reproducible builds and truthful release provenance."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from tools.release_metadata import installer_filename, read_version, source_metadata, write_manifest


class ReleaseMetadataTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.git("init", "-q")
        self.git("config", "user.name", "Release test")
        self.git("config", "user.email", "release-test@example.invalid")
        (self.root / "VERSION").write_text("0.1.2\n")
        (self.root / ".gitignore").write_text("build/\n")
        self.git("add", ".")
        self.git("commit", "-qm", "Fixture")

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], text=True).strip()

    def test_version_has_one_canonical_source(self):
        self.assertEqual(read_version(self.root), "0.1.2")
        for bad in ("0.1", "v0.1.2", "1.2.3.4", "01.2.3", "0.1.2\nextra", "65536.1.2"):
            (self.root / "VERSION").write_text(bad)
            with self.subTest(version=bad), self.assertRaises(ValueError):
                read_version(self.root)

    def test_dirty_and_untracked_inputs_cannot_claim_clean_commit(self):
        self.assertEqual(source_metadata(self.root)["source_commit"], self.git("rev-parse", "HEAD"))
        untracked = self.root / "untracked.py"
        untracked.write_text("print('not committed')")
        with self.assertRaisesRegex(ValueError, "clean checkout"):
            source_metadata(self.root)
        untracked.unlink()
        (self.root / "VERSION").write_text("0.1.3\n")
        with self.assertRaisesRegex(ValueError, "clean checkout"):
            source_metadata(self.root)

    def test_hashes_actual_candidate_without_touching_published_release(self):
        source = source_metadata(self.root)
        folder = self.root / "build" / "releases" / source["version"]
        folder.mkdir(parents=True)
        installer = folder / installer_filename(source["version"])
        content = b"MZfixture executable bytes"
        installer.write_bytes(content)
        metadata = write_manifest(installer, source["source_commit"], self.root)
        self.assertEqual(metadata["sha256"], hashlib.sha256(content).hexdigest().upper())
        self.assertEqual(json.loads((folder / "release.json").read_text()), metadata)
        self.assertFalse((self.root / "installer" / "release.json").exists())
        installer.write_text("version https://git-lfs.github.com/spec/v1\n")
        with self.assertRaisesRegex(ValueError, "not a Windows executable"):
            write_manifest(installer, source["source_commit"], self.root)

    def test_cannot_overwrite_published_release_or_mislabel_candidate(self):
        commit = source_metadata(self.root)["source_commit"]
        with self.assertRaisesRegex(ValueError, "preserve the verified release"):
            write_manifest(self.root / "installer" / installer_filename("0.1.2"), commit, self.root)
        with self.assertRaisesRegex(ValueError, "does not match VERSION"):
            write_manifest(self.root / "build" / installer_filename("9.9.9"), commit, self.root)

    def test_rejects_commit_changes_during_build(self):
        original = source_metadata(self.root)["source_commit"]
        (self.root / "VERSION").write_text("0.1.3\n")
        self.git("add", ".")
        self.git("commit", "-qm", "Changed while compiling")
        with self.assertRaisesRegex(ValueError, "changed during"):
            write_manifest(self.root / "not-used.exe", original, self.root)


if __name__ == "__main__":
    unittest.main()

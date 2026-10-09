"""Release provenance shared by the Windows build script and portable tests.

Candidate releases are staged outside installer/ until native verification is
complete. The shipped release manifest is intentionally not the source version.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
VERSION_PATTERN = re.compile(r"(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)")


def read_version(root: Path = ROOT) -> str:
    """Read the only maintained application version, not the old release's version."""
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    if not VERSION_PATTERN.fullmatch(version) or any(
        int(component) > 65535 for component in version.split(".") if component.isdigit()
    ):
        raise ValueError("VERSION must contain a three-part version such as 0.1.2.")
    return version


def git_output(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, encoding="utf-8"
    ).strip()


def source_metadata(root: Path = ROOT) -> dict[str, str]:
    """Reject uncommitted inputs so source_commit identifies the actual build."""
    if git_output(root, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError(
            "Release builds require a clean checkout, including untracked files. "
            "Commit or move your source changes before building."
        )
    commit = git_output(root, "rev-parse", "HEAD")
    if not re.fullmatch(r"[0-9a-f]{40,64}", commit):
        raise ValueError("Git did not return a complete source commit.")
    return {"version": read_version(root), "source_commit": commit}


def installer_filename(version: str) -> str:
    return f"StoryAtlasPreview-{version}-Windows-x64-Offline-Setup.exe"


def write_manifest(installer: Path, expected_commit: str, root: Path = ROOT) -> dict[str, str]:
    """Validate provenance again after compilation, then hash the actual EXE."""
    metadata = source_metadata(root)
    if metadata["source_commit"] != expected_commit:
        raise ValueError("The source commit changed during the build. Rebuild from one clean commit.")
    installer = installer.resolve()
    if installer.parent == (root / "installer").resolve():
        raise ValueError("Stage candidates outside installer/ to preserve the verified release.")
    if installer.name != installer_filename(metadata["version"]):
        raise ValueError("The candidate filename does not match VERSION.")
    with installer.open("rb") as file:
        if file.read(2) != b"MZ":
            raise ValueError("The candidate is not a Windows executable (it may be a Git LFS pointer).")
        file.seek(0)
        checksum = hashlib.file_digest(file, "sha256").hexdigest().upper()
    metadata.update(installer=installer.name, sha256=checksum)
    # Write metadata only after all validation, so a failed build is not promoted.
    installer.with_suffix(installer.suffix + ".sha256").write_text(
        f"{checksum}  {installer.name}\n", encoding="utf-8"
    )
    (installer.parent / "release.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--installer", type=Path, help="Write metadata for a staged candidate EXE.")
    parser.add_argument("--source-commit", help="Commit captured before the build began.")
    args = parser.parse_args()
    try:
        if args.installer:
            if not args.source_commit:
                parser.error("--source-commit is required with --installer")
            metadata = write_manifest(args.installer, args.source_commit)
        else:
            metadata = source_metadata()
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Release validation failed: {error}\n")
    print(json.dumps(metadata))


if __name__ == "__main__":
    main()

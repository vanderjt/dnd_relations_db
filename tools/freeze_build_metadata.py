"""Freeze the source fingerprint into the packaged build without relying on Git or a clock."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from story_atlas.version import APPLICATION_VERSION, CURRENT_VERSION, source_fingerprint

root = Path(__file__).resolve().parents[1]
manifest = root / "story_atlas" / "build_metadata.json"
manifest.write_text(json.dumps({"version": APPLICATION_VERSION, "schema": CURRENT_VERSION,
                                "fingerprint": source_fingerprint(root)}, indent=2) + "\n", encoding="utf-8")
print(f"Frozen Story Atlas {APPLICATION_VERSION} source {source_fingerprint(root)}")

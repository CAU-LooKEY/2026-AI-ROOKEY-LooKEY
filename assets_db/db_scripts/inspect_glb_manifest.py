"""Print manifest-ready structural facts from one or more GLB files."""

from __future__ import annotations

import hashlib
import json
import struct
import sys
from pathlib import Path


JSON_CHUNK_TYPE = 0x4E4F534A


def read_glb_json(path: Path) -> dict:
    with path.open("rb") as handle:
        magic, version, total_length = struct.unpack("<4sII", handle.read(12))
        if magic != b"glTF" or version != 2:
            raise ValueError(f"Unsupported GLB header: {path}")
        chunk_length, chunk_type = struct.unpack("<II", handle.read(8))
        if chunk_type != JSON_CHUNK_TYPE:
            raise ValueError(f"First GLB chunk is not JSON: {path}")
        document = json.loads(handle.read(chunk_length).decode("utf-8"))
    document["_totalLength"] = total_length
    return document


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("Expected at least one GLB path")
    for raw_path in sys.argv[1:]:
        path = Path(raw_path).resolve()
        document = read_glb_json(path)
        print(
            json.dumps(
                {
                    "path": str(path),
                    "bytes": path.stat().st_size,
                    "sha256": sha256(path),
                    "nodes": len(document.get("nodes", [])),
                    "meshes": len(document.get("meshes", [])),
                    "materials": len(document.get("materials", [])),
                    "textures": len(document.get("textures", [])),
                    "images": len(document.get("images", [])),
                    "extensionsUsed": document.get("extensionsUsed", []),
                    "namedPinNodes": sorted(
                        node.get("name")
                        for node in document.get("nodes", [])
                        if isinstance(node.get("name"), str)
                        and node["name"].startswith("pin_")
                    ),
                },
                separators=(",", ":"),
            )
        )


if __name__ == "__main__":
    main()

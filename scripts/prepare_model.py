"""Fetch a model on a connected build machine for inclusion in an offline package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Prepare a CTranslate2 Whisper model for the offline installer"
    )
    parser.add_argument(
        "--model",
        default="small",
        choices=("tiny", "tiny.en", "base", "base.en", "small", "small.en"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
    )
    args = parser.parse_args()
    output = args.output or Path(f"models/faster-whisper-{args.model}")

    from faster_whisper.utils import download_model

    output.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {args.model} to {output}...")
    download_model(args.model, output_dir=str(output))

    files = {
        path.name: {"bytes": path.stat().st_size, "sha256": sha256(path)}
        for path in sorted(output.iterdir())
        if path.is_file() and path.name != "soundflow-manifest.json"
    }
    manifest = {
        "format": 1,
        "engine": "faster-whisper",
        "model": args.model,
        "files": files,
    }
    manifest_path = output / "soundflow-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {len(files)} files; manifest: {manifest_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

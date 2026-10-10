#!/usr/bin/env python3
"""Push the card, the licence, the provenance, the original files and the Parquet to the Hub.

Uploaded, and nothing else: data/README.md, LICENSE and provenance.yaml; data/raw/2024/ (the
files listed in MANIFEST.json, unchanged, and the manifest and the CKAN package.json); and
data/parquet/2024/*.parquet, each declared as a config of the card. Publishing stops when
the card's licence is not cc-by-4.0, when the manifest lists a file as failed or a raw file's
sha256 differs from it, when a file under raw/ is not in the manifest, when another edition
sits under data/raw/, or when a Parquet is not declared in the card (or a declared one is
missing).

    uv run python src/publish.py             # dry run: the files and their total size
    uv run python src/publish.py --push
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
REPO = "yuiseki/nfgis-2024"
EDITION = "2024"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def collect(data: Path) -> list[str]:
    """The files to upload, relative to data/; stops on anything the rules above refute."""
    card = (data / "README.md").read_text(encoding="utf-8")
    front = card.split("---")[1] if card.startswith("---") else ""
    if not re.search(r"^license: cc-by-4\.0$", front, re.M):
        raise SystemExit("the card's licence must be cc-by-4.0 (PDL1.0, compatible with CC BY 4.0)")
    files = ["README.md", "LICENSE", "provenance.yaml"]

    raw = data / "raw"
    for d in sorted(p for p in raw.iterdir() if p.is_dir()):
        if d.name != EDITION:
            raise SystemExit(f"data/raw/{d.name}: only the {EDITION} edition is published")
    manifest = json.loads((raw / EDITION / "MANIFEST.json").read_text())
    if manifest.get("failed"):
        raise SystemExit(f"the manifest lists failed files: {sorted(manifest['failed'])}")
    names = set(manifest["files"]) | {"MANIFEST.json", "package.json"}
    for name, e in manifest["files"].items():
        if sha256(raw / EDITION / name) != e["sha256"]:
            raise SystemExit(f"raw/{EDITION}/{name} is not the file in its manifest")
    for p in sorted((raw / EDITION).iterdir()):
        if p.name not in names:
            raise SystemExit(f"raw/{EDITION}/{p.name} is not in the manifest")
    files += [f"raw/{EDITION}/{n}" for n in sorted(names)]

    declared = set(re.findall(r"data_files: (parquet/\S+\.parquet)", card))
    have = {f"parquet/{EDITION}/{p.name}" for p in (data / "parquet" / EDITION).glob("*.parquet")}
    for rel in sorted(have - declared):
        raise SystemExit(f"{rel} is not declared in the card")
    for rel in sorted(declared - have):
        raise SystemExit(f"the card declares {rel}, which does not exist")
    files += sorted(have)
    return files


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--push", action="store_true")
    a = ap.parse_args()

    files = collect(DATA)
    total = sum((DATA / f).stat().st_size for f in files)
    shown = [f for f in files if not f.startswith(("raw/", "parquet/"))]
    for f in shown:
        print(f"  {(DATA / f).stat().st_size:>14,}  {f}")
    print(f"  ({len(files) - len(shown)} raw and Parquet files not listed)")
    print(f"{a.repo}\n  {len(files)} files, {total:,} bytes ({total / 1e9:.2f} GB)")
    if not a.push:
        print("\ndry run. pass --push to upload")
        return 0

    from huggingface_hub import HfApi

    api = HfApi()
    api.create_repo(a.repo, repo_type="dataset", exist_ok=True, private=False)
    api.upload_folder(folder_path=str(DATA), repo_id=a.repo, repo_type="dataset",
                      allow_patterns=files)  # fmt: skip
    print(f"\npushed to https://huggingface.co/datasets/{a.repo}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

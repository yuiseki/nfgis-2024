#!/usr/bin/env python3
"""Check every source under data/raw/ against its MANIFEST.json.

For each file: it exists, has the manifest's size and sha256, and, when the catalogue stated
its size (the CKAN package does), that size. A .zip must be a readable zip whose members
all pass the CRC test; a .pdf must start with %PDF-; an .xlsx must be a readable zip.
Prints one line per source with the number of zips and of shapefiles inside them, and every
failure; exits non-zero on any failure.

    uv run python scripts/02_verify.py
"""

import importlib.util
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
_spec = importlib.util.spec_from_file_location("dl", Path(__file__).parent / "01_download.py")
dl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dl)


def verify_source(d: Path) -> list[str]:
    """Failures of one source directory (an empty list when it is sound)."""
    manifest = json.loads((d / "MANIFEST.json").read_text())
    failures = [f"{n}: failed to download ({e['error']})" for n, e in manifest.get("failed", {}).items()]
    for name, e in sorted(manifest["files"].items()):
        p = d / name
        if not p.is_file():
            failures.append(f"{name}: missing")
            continue
        if p.stat().st_size != e["bytes"] or dl.sha256_file(p) != e["sha256"]:
            failures.append(f"{name}: size or sha256 differs from the manifest")
            continue
        if e.get("catalogue_bytes") is not None and e["catalogue_bytes"] != e["bytes"]:
            failures.append(f"{name}: the catalogue states {e['catalogue_bytes']} bytes")
        if name.endswith((".zip", ".xlsx")):
            try:
                with zipfile.ZipFile(p) as z:
                    bad = z.testzip()
                if bad:
                    failures.append(f"{name}: member {bad} fails its CRC")
            except zipfile.BadZipFile:
                failures.append(f"{name}: not a readable zip")
        elif name.endswith(".pdf") and p.read_bytes()[:5] != b"%PDF-":
            failures.append(f"{name}: not a PDF")
    return failures


def shapefiles(d: Path) -> tuple[int, int]:
    n = z = 0
    for p in sorted(d.glob("*.zip")):
        try:
            with zipfile.ZipFile(p) as zf:
                z += 1
                n += sum(1 for m in zf.namelist() if m.lower().endswith(".shp"))
        except zipfile.BadZipFile:
            pass
    return z, n


def main() -> int:
    dirs = sorted(p.parent for p in RAW.glob("*/MANIFEST.json"))
    if not dirs:
        print("FAIL no MANIFEST.json under data/raw/")
        return 1
    total = 0
    for d in dirs:
        files = len(json.loads((d / "MANIFEST.json").read_text())["files"])
        failures = verify_source(d)
        z, n = shapefiles(d)
        print(f"{'ok  ' if not failures else 'FAIL'} {d.name}: {files} files, {z} zips, {n} shapefiles")
        for f in failures:
            print(f"  FAIL {f}")
        total += len(failures)
    print("all ok" if not total else f"{total} failure(s)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Fetch the national forest GIS data of Japan's Forestry Agency (林野庁 国有林GISデータ).

Two distributions of the same small-compartment (小班) polygons are collected, each under
data/raw/<source>/ with a MANIFEST.json:

    nfgis-2024    国有林GISデータ 2024 (令和6) 年度版, reference date 2024-04-01, published by the
                  Forestry Agency on the G-Spatial Information Center CKAN
                  (https://www.geospatial.jp/ckan/dataset/nfgis-2024): 47 prefecture zips,
                  the terms PDFs, the specification and the code table. The file list comes
                  from the CKAN package_show API.
    ksj-a45-2019  国土数値情報 A45 国有林野 2019 (令和元) 年度版, reference date 2018-04-01, the
                  older edition the Ministry of Land, Infrastructure, Transport and Tourism
                  distributes (https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-A45.html):
                  47 prefecture zips and the product specification. The file list comes from the
                  DownLd(...) calls in that page, which is saved too.

Nothing is guessed: every URL is read from the catalogue or the page. Files are written to
.part, resumed with Range when the server allows it, checked against Content-Length, hashed
while streaming, and renamed. The manifest is rewritten after every file, so an interrupted
run continues where it stopped: a file whose manifest entry has the same URL, size and
sha256 is skipped. Requests are sequential, one second apart; a 401, 403 or 429 stops the run.

    uv run python scripts/01_download.py --dry-run      # the plan and its sizes
    uv run python scripts/01_download.py                # everything (about 3 GB)
    uv run python scripts/01_download.py --only ksj-a45-2019 --limit 3
"""

import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
EDITION = "2024"
UA = "nfgis-2024/1 (+https://github.com/yuiseki/nfgis-2024)"
DELAY = 1.0
WAITS = (30, 120, 300)
CKAN_URL = "https://www.geospatial.jp/ckan/api/3/action/package_show?id=nfgis-2024"
CKAN_PAGE = "https://www.geospatial.jp/ckan/dataset/nfgis-2024"


class Incomplete(Exception):
    """The server sent fewer bytes than it promised; the .part file is kept."""


class Failed(Exception):
    """A file no URL candidate could deliver; the run records it and goes on."""


def safe_name(name: str) -> str:
    if not name or name in (".", "..") or "/" in name or "\\" in name or "\x00" in name:
        raise SystemExit(f"unsafe file name: {name!r}")
    return name


def ckan_links(package: dict) -> list[dict]:
    """Resources that are links to a page, not files (the terms of use link)."""
    return [{"name": r["name"], "url": r["url"]}
            for r in package["result"]["resources"] if r.get("format") == "URL"]  # fmt: skip


def ckan_plan(package: dict) -> list[dict]:
    """The files of the CKAN package: name, url, bytes the catalogue states, resource id."""
    plan, seen = [], set()
    for r in package["result"]["resources"]:
        if r.get("format") == "URL":
            continue
        ext = "." + r["format"].lower()
        name = safe_name(r["name"] if r["name"].lower().endswith(ext) else r["name"] + ext)
        if name in seen:
            raise SystemExit(f"two resources with the same file name: {name}")
        seen.add(name)
        plan.append({"name": name, "url": r["url"], "bytes": r.get("size"), "resource_id": r["id"]})
    return plan


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def is_current(path: Path, entry: dict, url: str) -> bool:
    """The file is the one the manifest says: same catalogue URL, size and sha256."""
    return (path.is_file() and entry.get("catalogue_url", entry.get("url")) == url
            and path.stat().st_size == entry["bytes"]
            and sha256_file(path) == entry["sha256"])  # fmt: skip


def candidates(url: str) -> list[str]:
    """The catalogue URL, then the same URL with "www.geospatial.jp" taken off the front of
    its file name. The CKAN package lists most files as ".../download/www.geospatial.jp01.zip",
    which the server answers with HTTP 500; ".../download/01.zip" delivers the file whose size
    the catalogue states."""
    head, _, tail = url.rpartition("/")
    stripped = tail.replace("www.geospatial.jp", "", 1)
    return [url] if stripped == tail or not stripped else [url, f"{head}/{stripped}"]


def fetch(url: str, dest: Path) -> dict:
    """Download url to dest through dest.part; return its manifest entry."""
    part = dest.with_name(dest.name + ".part")
    have = part.stat().st_size if part.exists() else 0
    headers = {"User-Agent": UA}
    if have:
        headers["Range"] = f"bytes={have}-"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as resp:
        if have and resp.status != 206:
            have = 0  # the server ignored Range: start again
        total = have + int(resp.headers["Content-Length"]) if resp.headers.get("Content-Length") else None
        h = hashlib.sha256()
        if have:
            with open(part, "rb") as f:
                for block in iter(lambda: f.read(1 << 20), b""):
                    h.update(block)
        with open(part, "ab" if have else "wb") as f:
            while block := resp.read(1 << 20):
                f.write(block)
                h.update(block)
        size = part.stat().st_size
        if total is not None and size != total:
            raise Incomplete(f"{url}: got {size} of {total} bytes")
        entry = {
            "url": url, "bytes": size, "sha256": h.hexdigest(),
            "last_modified": resp.headers.get("Last-Modified"), "etag": resp.headers.get("ETag"),
            "fetched_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }  # fmt: skip
    part.replace(dest)
    return entry


def get_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def fetch_with_retries(url: str, dest: Path) -> dict:
    """Fetch url, or the next candidate after an HTTP 500; wait and retry only for 502/503/504
    and network errors. 401, 403 and 429 stop the whole run. Raises Failed when nothing works."""
    last = "no candidate"
    for cand in candidates(url):
        for attempt in range(len(WAITS) + 1):
            try:
                return fetch(cand, dest)
            except urllib.error.HTTPError as e:
                if e.code in (401, 403, 429):
                    raise SystemExit(f"HTTP {e.code} from {cand}: stopping, check before resuming") from e
                last = f"HTTP {e.code} from {cand}"
                if e.code == 416:  # the .part is complete or stale: start again
                    dest.with_name(dest.name + ".part").unlink(missing_ok=True)
                elif e.code in (502, 503, 504):
                    pass
                else:
                    break  # a 500 or 404 will not change: try the next candidate
            except (Incomplete, urllib.error.URLError, TimeoutError, ConnectionError) as e:
                last = str(e)
            print(f"  {last}", flush=True)
            if attempt == len(WAITS):
                break
            print(f"  waiting {WAITS[attempt]} s", flush=True)
            time.sleep(WAITS[attempt])
    raise Failed(last)


def load_manifest(d: Path) -> dict:
    p = d / "MANIFEST.json"
    return json.loads(p.read_text()) if p.exists() else {"files": {}}


def save_manifest(d: Path, manifest: dict) -> None:
    tmp = d / "MANIFEST.json.tmp"
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n")
    tmp.replace(d / "MANIFEST.json")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="fetch at most N files")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    package = json.loads(get_bytes(CKAN_URL))
    time.sleep(DELAY)
    pkg = package["result"]
    files = ckan_plan(package)[: a.limit] if a.limit else ckan_plan(package)
    stated = sum(int(f["bytes"] or 0) for f in files)
    print(f"nfgis-{EDITION}: {len(files)} files, about {stated / 1e9:.2f} GB", flush=True)
    if a.dry_run:
        return 0
    d = RAW / EDITION
    d.mkdir(parents=True, exist_ok=True)
    (d / "package.json").write_text(json.dumps(package, ensure_ascii=False, indent=1))
    manifest = load_manifest(d)
    manifest.update({
        "catalogue": CKAN_PAGE, "title": pkg.get("title"), "license_id": pkg.get("license_id"),
        "license_title": pkg.get("license_title"), "metadata_modified": pkg.get("metadata_modified"),
        "links": ckan_links(package),
    })  # fmt: skip
    manifest.setdefault("failed", {})
    for i, f in enumerate(files, 1):
        dest = d / f["name"]
        entry = manifest["files"].get(f["name"], {})
        if entry and is_current(dest, entry, f["url"]):
            continue
        print(f"[{i}/{len(files)}] {f['name']}", flush=True)
        time.sleep(DELAY)
        try:
            entry = fetch_with_retries(f["url"], dest)
        except Failed as e:
            print(f"  FAILED {f['name']}: {e}", flush=True)
            manifest["failed"][f["name"]] = {"catalogue_url": f["url"], "error": str(e)}
            save_manifest(d, manifest)
            continue
        if f.get("bytes") and entry["bytes"] != int(f["bytes"]):
            print(f"  note: the catalogue states {f['bytes']} bytes, got {entry['bytes']}")
        entry.update({"catalogue_url": f["url"], "resource_id": f.get("resource_id"),
                      "catalogue_bytes": int(f["bytes"]) if f.get("bytes") else None})  # fmt: skip
        manifest["files"][f["name"]] = entry
        manifest["failed"].pop(f["name"], None)
        save_manifest(d, manifest)
    save_manifest(d, manifest)
    if manifest["failed"]:
        print(f"{len(manifest['failed'])} file(s) failed; run again to retry them", flush=True)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

import importlib.util
import json
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
_spec = importlib.util.spec_from_file_location("vf", HERE.parent / "scripts" / "02_verify.py")
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)
_dspec = importlib.util.spec_from_file_location("dl", HERE.parent / "scripts" / "01_download.py")
dl = importlib.util.module_from_spec(_dspec)
_dspec.loader.exec_module(dl)


def make_source(root: Path, files: dict[str, bytes]) -> Path:
    d = root / "src"
    d.mkdir()
    manifest = {"files": {}}
    for name, data in files.items():
        (d / name).write_bytes(data)
        manifest["files"][name] = {"url": f"https://x/{name}", "bytes": len(data),
                                   "sha256": dl.sha256_file(d / name)}  # fmt: skip
    (d / "MANIFEST.json").write_text(json.dumps(manifest))
    return d


def zip_bytes(tmp_path: Path, members: dict[str, bytes]) -> bytes:
    p = tmp_path / "t.zip"
    with zipfile.ZipFile(p, "w") as z:
        for k, v in members.items():
            z.writestr(k, v)
    return p.read_bytes()


def test_a_sound_source_passes(tmp_path):
    z = zip_bytes(tmp_path, {"a/x.shp": b"1", "a/x.dbf": b"2"})
    d = make_source(tmp_path, {"a.zip": z, "s.pdf": b"%PDF-1.4 x"})
    assert m.verify_source(d) == []


def test_a_changed_file_fails(tmp_path):
    z = zip_bytes(tmp_path, {"a/x.shp": b"1"})
    d = make_source(tmp_path, {"a.zip": z})
    (d / "a.zip").write_bytes(z[:-1] + b"?")
    assert any("sha256" in f or "size" in f for f in m.verify_source(d))


def test_a_corrupt_zip_fails(tmp_path):
    d = make_source(tmp_path, {"a.zip": b"not a zip"})
    assert any("not a readable zip" in f for f in m.verify_source(d))


def test_a_pdf_without_its_header_fails(tmp_path):
    d = make_source(tmp_path, {"s.pdf": b"<html>blocked</html>"})
    assert any("not a PDF" in f for f in m.verify_source(d))


def test_a_missing_file_fails(tmp_path):
    z = zip_bytes(tmp_path, {"a/x.shp": b"1"})
    d = make_source(tmp_path, {"a.zip": z})
    (d / "a.zip").unlink()
    assert any("missing" in f for f in m.verify_source(d))


def test_a_catalogue_size_that_differs_fails(tmp_path):
    z = zip_bytes(tmp_path, {"a/x.shp": b"1"})
    d = make_source(tmp_path, {"a.zip": z})
    manifest = json.loads((d / "MANIFEST.json").read_text())
    manifest["files"]["a.zip"]["catalogue_bytes"] = len(z) + 5
    (d / "MANIFEST.json").write_text(json.dumps(manifest))
    assert any("catalogue" in f for f in m.verify_source(d))


def test_a_file_recorded_as_failed_fails(tmp_path):
    z = zip_bytes(tmp_path, {"a/x.shp": b"1"})
    d = make_source(tmp_path, {"a.zip": z})
    manifest = json.loads((d / "MANIFEST.json").read_text())
    manifest["failed"] = {"b.zip": {"catalogue_url": "https://x/b.zip", "error": "HTTP 500"}}
    (d / "MANIFEST.json").write_text(json.dumps(manifest))
    assert any("b.zip" in f and "failed to download" in f for f in m.verify_source(d))

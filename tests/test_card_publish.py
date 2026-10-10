import hashlib
import importlib.util
import json
from pathlib import Path

import duckdb
import pytest

HERE = Path(__file__).parent


def load(file):
    spec = importlib.util.spec_from_file_location(file, HERE.parent / file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


card = load("scripts/06_card.py")
pub = load("src/publish.py")

INDEX = [
    # source, layer, zone, epsg, rows, output
    ("13東京都/48/第9系/小班区画.shp", "小班区画", 9, 2451, 454, "shouhan_zone09.parquet"),
    ("13東京都/49/第9系/小班区画.shp", "小班区画", 9, 2451, 98, "shouhan_zone09.parquet"),
    ("13東京都/49/第14系/林道.shp", "林道", 14, 2456, 0, None),
    ("13東京都/49/第9系/林道.shp", "林道", 9, 2451, 7, "rindou_zone09.parquet"),
]


def test_groups_are_one_per_output_file_in_layer_then_zone_order():
    g = card.groups(INDEX)
    assert [(x["output"], x["rows"], x["files"], x["epsg"]) for x in g] == [
        ("shouhan_zone09.parquet", 552, 2, 2451), ("rindou_zone09.parquet", 7, 1, 2451)]  # fmt: skip
    assert card.empty_sources(INDEX) == ["13東京都/49/第14系/林道.shp"]


def test_configs_declare_the_index_and_every_file():
    y = card.configs_yaml(card.groups(INDEX))
    assert "- config_name: 'index'\n  data_files: parquet/2024/index.parquet\n  default: true" in y
    assert "- config_name: 'shouhan_zone09'\n  data_files: parquet/2024/shouhan_zone09.parquet" in y
    assert y.count("config_name") == 3


def make_data(tmp_path, card_files=("index", "shouhan_zone09"), manifest_ok=True, extra=None):
    d = tmp_path / "data"
    (d / "parquet" / "2024").mkdir(parents=True)
    (d / "raw" / "2024").mkdir(parents=True)
    for name in ("index", "shouhan_zone09"):
        (d / "parquet" / "2024" / f"{name}.parquet").write_bytes(b"PAR1")
    (d / "raw" / "2024" / "a.zip").write_bytes(b"zip")
    sha = hashlib.sha256(b"zip" if manifest_ok else b"other").hexdigest()
    (d / "raw" / "2024" / "MANIFEST.json").write_text(json.dumps(
        {"files": {"a.zip": {"bytes": 3, "sha256": sha}}, "failed": {}}))
    (d / "raw" / "2024" / "package.json").write_text("{}")
    cfg = "".join(f"- config_name: '{n}'\n  data_files: parquet/2024/{n}.parquet\n" for n in card_files)
    (d / "README.md").write_text(f"---\nlicense: cc-by-4.0\nconfigs:\n{cfg}---\n")
    for f in ("LICENSE", "provenance.yaml"):
        (d / f).write_text("x")
    for rel in extra or []:
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        (d / rel).write_bytes(b"x")
    return d


def test_collect_lists_the_card_the_raw_files_and_the_parquet(tmp_path):
    files = pub.collect(make_data(tmp_path))
    assert files == [
        "README.md", "LICENSE", "provenance.yaml", "raw/2024/MANIFEST.json",
        "raw/2024/a.zip", "raw/2024/package.json", "parquet/2024/index.parquet",
        "parquet/2024/shouhan_zone09.parquet"]  # fmt: skip


def test_a_parquet_the_card_does_not_declare_stops_it(tmp_path):
    with pytest.raises(SystemExit, match="shouhan_zone09"):
        pub.collect(make_data(tmp_path, card_files=("index",)))


def test_a_raw_file_unlike_its_manifest_stops_it(tmp_path):
    with pytest.raises(SystemExit, match="a.zip"):
        pub.collect(make_data(tmp_path, manifest_ok=False))


def test_a_file_the_manifest_lists_as_failed_stops_it(tmp_path):
    d = make_data(tmp_path)
    m = json.loads((d / "raw/2024/MANIFEST.json").read_text())
    m["failed"] = {"b.zip": {"error": "HTTP 500"}}
    (d / "raw/2024/MANIFEST.json").write_text(json.dumps(m))
    with pytest.raises(SystemExit, match="failed"):
        pub.collect(d)


def test_a_stray_file_under_raw_or_parquet_is_refused(tmp_path):
    with pytest.raises(SystemExit, match="not in the manifest"):
        pub.collect(make_data(tmp_path, extra=["raw/2024/stray.zip"]))
    with pytest.raises(SystemExit, match="declared"):
        pub.collect(make_data(tmp_path / "b", extra=["parquet/2024/other.parquet"]))


def test_the_ksj_edition_never_goes_up(tmp_path):
    with pytest.raises(SystemExit, match="2024"):
        pub.collect(make_data(tmp_path, extra=["raw/2019/A45-19_01_GML.zip"]))


def test_the_card_must_declare_cc_by(tmp_path):
    d = make_data(tmp_path)
    (d / "README.md").write_text((d / "README.md").read_text().replace("cc-by-4.0", "mit"))
    with pytest.raises(SystemExit, match="licen"):
        pub.collect(d)


def test_duckdb_is_available_for_the_card_script():
    assert duckdb.__version__

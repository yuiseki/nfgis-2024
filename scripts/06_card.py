#!/usr/bin/env python3
"""Write the dataset card, the licence and the provenance from what is on disk.

    data/README.md        the Hugging Face card (English), with one config per Parquet file
    data/LICENSE          the Forestry Agency's two terms documents, quoted from their PDFs
    data/provenance.yaml  source, files, counts, how the Parquet was made, what was checked

Reads data/parquet/2024/index.parquet and the Parquet files (counts, columns, invalid
geometries), data/raw/2024/MANIFEST.json and package.json, and the two terms PDFs (through
pdftotext, from poppler). Run after scripts/03_export_parquet.py and 05_verify_parquet.py.

    uv run python scripts/06_card.py
"""

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "2024"
PQ = ROOT / "data" / "parquet" / "2024"
DATA = ROOT / "data"
_spec = importlib.util.spec_from_file_location("export", Path(__file__).parent / "03_export_parquet.py")
export = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(export)
LAYERS = export.LAYERS
EN = {"小班区画": "small compartments (polygons)", "林班区画": "compartments (polygons)",
      "林道": "forest roads (lines)"}  # fmt: skip
TERMS_IMPORTANT = "公共データ利用規約（第1.0版）に関する重要情報.pdf"
TERMS_NOTES = "国有林GISデータの利用に当たっての留意事項.pdf"
GLOSS = {
    "ID": "identifier: digits of the codes below, zero padded (23 digits for a small compartment, 19 for a compartment, 14 for a road)",
    "森林管理局": "forest management bureau code", "森林管理署": "forest office code",
    "林班主番": "compartment number", "林班枝番": "compartment branch number (0 if none)",
    "小班主番": "small compartment number", "小班枝番": "small compartment branch number (0 if none)",
    "局名称": "bureau name", "署名称": "office name", "小班名": "small compartment name",
    "林小班名称": "combined compartment and small compartment name",
    "材積": "timber volume of the small compartment, m3", "国有林名": "national forest name",
    "担当区": "district", "県市町村": "municipality",
    "樹種１": "tree species with the largest area share", "樹立林齢１": "its age when the forest plan was made",
    "樹種２": "second largest species", "樹立林齢２": "its age", "樹種３": "third largest species",
    "樹立林齢３": "its age", "計画区": "forest planning area", "林種の細分": "forest type (e.g. 天 natural forest, 単 single-layer plantation)",
    "機能類型": "function to be emphasised", "面積": "area of the small compartment, ha",
    "保安林１": "protection forest type 1", "保安林２": "type 2", "保安林３": "type 3", "保安林４": "type 4",
    "保護林": "code of the protected forest it is set in", "緑の回廊": "code of the green corridor",
    "樹立年度": "fiscal year of the forest plan", "路線番号": "road route number", "林道名": "road name",
}  # fmt: skip


def groups(index: list[tuple]) -> list[dict]:
    """One entry per Parquet file, in layer then zone order: rows, source shapefiles, EPSG."""
    order = {n: i for i, n in enumerate(LAYERS)}
    out: dict[str, dict] = {}
    for _source, layer, zone, epsg, rows, output in index:
        if output is None:
            continue
        g = out.setdefault(output, {"output": output, "layer": layer, "zone": zone,
                                    "epsg": epsg, "rows": 0, "files": 0})  # fmt: skip
        g["rows"] += rows
        g["files"] += 1
    return sorted(out.values(), key=lambda g: (order[g["layer"]], g["zone"]))


def empty_sources(index: list[tuple]) -> list[str]:
    return [r[0] for r in index if r[5] is None]


def configs_yaml(gs: list[dict]) -> str:
    y = "- config_name: 'index'\n  data_files: parquet/2024/index.parquet\n  default: true\n"
    for g in gs:
        name = g["output"].removesuffix(".parquet")
        y += f"- config_name: '{name}'\n  data_files: parquet/2024/{g['output']}\n"
    return y


def pdf_text(name: str) -> str:
    out = subprocess.run(["pdftotext", "-layout", str(RAW / name), "-"], capture_output=True,
                         text=True, check=True).stdout
    return "\n".join(re.sub(r"\s+", " ", ln).strip() for ln in out.splitlines() if ln.strip())


def to_yaml(obj, indent=0) -> str:
    pad = "  " * indent
    if isinstance(obj, dict):
        return "".join(
            f"{pad}{json.dumps(k, ensure_ascii=False)}:" +
            (f"\n{to_yaml(v, indent + 1)}" if isinstance(v, (dict, list)) and v else
             f" {json.dumps(v, ensure_ascii=False) if not isinstance(v, (dict, list)) else ('{}' if isinstance(v, dict) else '[]')}\n")
            for k, v in obj.items())  # fmt: skip
    return "".join(f"{pad}- {json.dumps(v, ensure_ascii=False)}\n" if not isinstance(v, (dict, list))
                   else f"{pad}-\n{to_yaml(v, indent + 1)}" for v in obj)


def facts():
    import duckdb

    con = duckdb.connect()
    con.execute("load spatial")
    con.execute("set enable_geoparquet_conversion = false")
    index = con.sql(f"select source, layer, zone, epsg, rows, output from '{PQ / 'index.parquet'}' order by source").fetchall()
    gs = groups(index)
    cols, invalid, rows = {}, {}, {}
    for layer in LAYERS:
        files = [g for g in gs if g["layer"] == layer]
        sample = PQ / files[0]["output"]
        cols[layer] = [(n, t) for n, t, *_ in con.sql(f"describe select * from '{sample}'").fetchall()
                       if n not in ("file_index", "record", "source", "geometry", "bbox")]
        invalid[layer] = sum(con.sql(
            f"select count(*) from '{PQ / g['output']}' where geometry is not null "
            "and not ST_IsValid(ST_GeomFromWKB(geometry))").fetchone()[0] for g in files)
        rows[layer] = sum(g["rows"] for g in files)
    return index, gs, cols, invalid, rows


def card_text(index, gs, cols, invalid, rows, manifest, package) -> str:
    pkg = package["result"]
    fetched = sorted(e["fetched_at"] for e in manifest["files"].values())
    prefectures = len({r[0].split("/")[0] for r in index})
    areas = len({tuple(r[0].split("/")[:2]) for r in index})
    groups_table = "\n".join(
        f"| `{g['output']}` | {g['layer']} {EN[g['layer']].split(' (')[0]} | 第{g['zone']}系 | EPSG:{g['epsg']} | {g['files']} | {g['rows']:,} |"
        for g in gs)
    col_tables = ""
    for layer in LAYERS:
        col_tables += f"\n`{LAYERS[layer]}_zone*.parquet` ({layer}, {rows[layer]:,} rows, {invalid[layer]:,} invalid geometries):\n\n| column | type | meaning |\n|---|---|---|\n"
        col_tables += "\n".join(f"| `{n}` | {t} | {GLOSS.get(n, '')} |" for n, t in cols[layer]) + "\n"
    empties = "\n".join(f"- `{s}`" for s in empty_sources(index))
    return f"""---
license: cc-by-4.0
language:
- ja
tags:
- forestry
- national-forest
- japan
- gis
- geoparquet
- shapefile
pretty_name: Japan national forest GIS data (Forestry Agency, 2024 edition)
size_categories:
- 1M<n<10M
configs:
{configs_yaml(gs)}---

# nfgis-2024

The national forest GIS data (国有林GISデータ), 2024 edition, of Japan's Forestry Agency
(林野庁): the small compartments (小班区画, {rows['小班区画']:,} polygons), the compartments
(林班区画, {rows['林班区画']:,} polygons) and the forest roads (林道, {rows['林道']:,} lines) of the
national forests, in the shapefiles the Agency publishes and as GeoParquet. Reference date
2024-04-01, forest plans up to FY2023 (令和5年度).

- Official source: the G-Spatial Information Center,
  <https://www.geospatial.jp/ckan/dataset/nfgis-2024> (publisher 林野庁 国有林野部 経営企画課,
  published 2025-12, record last modified {pkg.get('metadata_modified', '')[:10]}).
- Licence: the Public Data License 1.0 (PDL1.0, compatible with CC BY 4.0); see Licence.
- Code: <https://github.com/yuiseki/nfgis-2024> (download, verify, export, card).

## What is here

| path | what |
|---|---|
| `raw/2024/` | the {len(manifest['files'])} files of the CKAN package, unchanged: {sum(1 for n in manifest['files'] if n.endswith('.zip'))} prefecture zips of shapefiles, the specification, the code table, the two terms PDFs; `MANIFEST.json` (URL, size, sha256, fetch time) and `package.json` (the catalogue record) |
| `parquet/2024/` | one GeoParquet per layer and zone, and `index.parquet` |

The files were fetched {fetched[0][:10]} to {fetched[-1][:10]}. This dataset is the 2024 edition; a later
edition would be added beside it, not over it.

## The shapefiles and how the Parquet is split

Each prefecture zip holds `<prefecture>/<forest planning area>/第N系/<layer>.shp`:
{len(index)} shapefiles ({prefectures} prefectures, {areas} planning areas) in 17 zones of the
JGD2000 plane rectangular coordinate system. A zone is a coordinate system, so the Parquet
is split by layer and zone and the coordinates are exactly as published, never reprojected.
Each file carries the CRS of its zone (EPSG:2443 for 第1系 up to EPSG:2461 for 第19系) in its
GeoParquet metadata. `index.parquet` has one row per source shapefile (`source`, `prefecture`,
`planning_area`, `layer`, `zone`, `epsg`, `rows`, `output`).

| file | layer | zone | CRS | shapefiles | rows |
|---|---|---|---|---:|---:|
{groups_table}

Shapefiles with no features have no Parquet file; `index.parquet` lists them with 0 rows and
`output` NULL:

{empties}

## Columns

Every file starts with `file_index` (the shapefile's position in the group, by its path in the
zip), `record` (its DBF record number, 0 based) and `source` (the path inside the zip), then the
attributes under their published names, then `geometry` (WKB) and `bbox` (a struct xmin, ymin,
xmax, ymax of the geometry, the GeoParquet 1.1 covering). All shapefiles of a layer have the same
attributes. Types are the DBF field types: text is VARCHAR (also the digit strings such as
the ID, which keep their leading zeros), a number with no decimals BIGINT, a number with decimals
DOUBLE. Text is stripped of spaces and an empty text or number is NULL.
{col_tables}
## How the Parquet was made

`scripts/03_export_parquet.py` reads each DBF with the standard library (its field names and
values are Shift_JIS) and each geometry with DuckDB's ST_Read, and joins them by record number.
The DBF is decoded as Microsoft's cp932, the code page of the Windows tools that made it: six
codes (0x817C, 0x8160, 0x8161, 0x8191, 0x8192, 0x81CA) become the full-width forms
(U+FF0D, U+FF5E, U+2225, U+FFE0, U+FFE1, U+FFE2) where a JIS X 0208 decoder (iconv) gives
U+2212, U+301C, U+2016, U+00A2, U+00A3, U+00AC. The shapefiles have no `.cpg`; their DBF header
says Shift_JIS. Rows keep the order of the shapefiles. The Parquet is zstd compressed, in row
groups of 10,000 rows, without bloom filters, and `geo` metadata is GeoParquet 1.1.0.

## Things to know

- The Agency says the data was made for its administrative work under the Forest Act and the
  National Forest Management Act and not for other uses, that positions, areas, forest types and
  species may differ from the ground (some come from aerial photo interpretation or carry errors
  from the way the data was made), that it shows the forests as of the time of creation, and that
  it does not prove ownership, boundaries or the value of standing trees. The full text is in
  `LICENSE`. Entry to national forests usually needs a prior procedure (入林手続).
- {sum(invalid.values()):,} geometries are not valid by the OGC rules ({invalid['小班区画']:,} small
  compartments, {invalid['林班区画']:,} compartments, {invalid['林道']:,} roads). They are kept as
  published; fix them (for example with ST_MakeValid) before computing with them.
- `樹立林齢１` to `樹立林齢３` and `樹立年度` are text in the DBF and stay text here.
- The specification says each data unit is a forest planning area ("データ単位 森林計画区"); a
  planning area on islands in more than one zone (for example 49伊豆諸島森林計画区, zones 9, 14
  and 19) has a shapefile per zone, so it appears in more than one Parquet file.

## Checked before upload

`scripts/05_verify_parquet.py` checks, for all {len(index)} source shapefiles:

- every attribute of every feature ({sum(rows.values()):,} in all) equals what GDAL
  (3.9.2, `SHAPE_ENCODING=CP932`, the six characters above put in Microsoft's forms) reads from the
  same shapefile, through a digest per shapefile (`scripts/04_gdal_digests.py`)
- each record's bounding box and number of points in the `.shp` header equal the Parquet row's
  `bbox` and the number of points of its WKB; no `.shp` record lacks a row
- every Parquet file is in `(file_index, record)` order, has GeoParquet 1.1.0 metadata with the
  CRS of its zone, the bbox of its rows and the covering, has no bloom filter, and opens in a
  DuckDB with extension autoloading turned off
- `scripts/02_verify.py` checked every raw file against `MANIFEST.json` (size, sha256, zip CRCs)

## Licence

The Forestry Agency's "「公共データ利用規約（第1.0版）に関する重要情報」" (the PDF in `raw/2024/`,
quoted in full in `LICENSE`) applies the Public Data License 1.0
(<https://www.digital.go.jp/resources/open_data/public_data_license_v1.0>), which says it is
compatible with CC BY 4.0, hence `cc-by-4.0` above. The catalogue calls the licence `ol` (the
Agency's own terms: this document). Its conditions:

> 本コンテンツを利用する際は、出典を記載してください。
> （出典記載例）出典：国有林 GIS データ（当該ページの URL）、PDL1.0
> 本コンテンツを編集・加工等して利用する場合は、上記出典とは別に、編集・加工等を行ったことを記載してください。なお、編集・加工した情報を、あたかも林野庁が作成したかのような態様で公表・利用してはいけません。

The Parquet files and `index.parquet` are an edited form made by yuiseki/nfgis-2024, not a
Forestry Agency product, and the Agency has not reviewed them: when you use them, say they were
processed, for example 「国有林 GIS データ（https://www.geospatial.jp/ckan/dataset/nfgis-2024）を加工して作成」.
What was changed is listed in `LICENSE`. The files under `raw/2024/` are the Agency's, unchanged.

## Citation

> 林野庁「国有林 GIS データ」（2024（令和6）年度版、基準時点 2024-04-01）、G空間情報センター
> https://www.geospatial.jp/ckan/dataset/nfgis-2024 、PDL1.0
"""


def license_text(index, rows) -> str:
    return f"""Licence of nfgis-2024

The data is the Forestry Agency's national forest GIS data (国有林GISデータ), 2024 edition,
from https://www.geospatial.jp/ckan/dataset/nfgis-2024. The Agency applies the Public Data
License 1.0 (PDL1.0, https://www.digital.go.jp/resources/open_data/public_data_license_v1.0),
which states that it is compatible with the Creative Commons Attribution 4.0 International
licence. The catalogue names the licence "ol" (other open licence); the Agency's own terms are
the two documents below, which are the PDFs in raw/2024/, quoted as pdftotext reads them.

1. 公共データ利用規約（第1.0版）に関する重要情報.pdf

{pdf_text(TERMS_IMPORTANT)}

2. 国有林GISデータの利用に当たっての留意事項.pdf

{pdf_text(TERMS_NOTES)}

What this dataset changes. The files under raw/2024/ are the Agency's, byte for byte. The
Parquet under parquet/2024/ was made from the shapefiles in those zips:

  - the DBF was decoded from Shift_JIS (Microsoft cp932) and written as UTF-8; text was
    stripped of spaces and an empty text or number became NULL; numbers were typed by their
    DBF field type; no value was otherwise changed
  - the geometry was copied as WKB without change, the coordinates are as published
  - the columns file_index, record, source and bbox were added, and the layer was split by
    plane rectangular zone, with the shapefiles of the prefecture zips concatenated in the order
    of their paths
  - parquet/2024/index.parquet lists the source shapefiles with their row counts

This dataset is not made or endorsed by the Forestry Agency. The code in
https://github.com/yuiseki/nfgis-2024 is MIT licensed and does not apply to the data.
"""


def provenance(index, gs, rows, invalid, manifest, package) -> dict:
    pkg = package["result"]
    return {
        "source": {
            "name": "国有林GISデータ (national forest GIS data), 2024 edition",
            "publisher": "林野庁 国有林野部 経営企画課 (Forestry Agency)",
            "catalogue": "https://www.geospatial.jp/ckan/dataset/nfgis-2024",
            "catalogue_record_modified": pkg.get("metadata_modified"),
            "reference_date": "2024-04-01",
            "specification_published": "2025-12-25",
            "licence": {"applied": "Public Data License 1.0 (PDL1.0)",
                        "catalogue_license_id": pkg.get("license_id"),
                        "terms": [TERMS_IMPORTANT, TERMS_NOTES],
                        "card": "license: cc-by-4.0"},  # fmt: skip
        },
        "files": {"count": len(manifest["files"]), "fetched_from": min(e["fetched_at"] for e in manifest["files"].values()),
                  "fetched_to": max(e["fetched_at"] for e in manifest["files"].values()),
                  "manifest": "raw/2024/MANIFEST.json"},  # fmt: skip
        "shapefiles": {"count": len(index), "features": sum(rows.values()), "by_layer": rows,
                       "empty": empty_sources(index)},  # fmt: skip
        "parquet": {"files": len(gs), "crs": "EPSG:2443 to EPSG:2461 by zone, as published",
                    "invalid_geometries": invalid, "decoding": "Microsoft cp932"},  # fmt: skip
        "checked": ["raw files against MANIFEST.json (size, sha256, zip CRC)",
                    "every attribute against GDAL by digest, every record's bbox and point count against the .shp header",
                    "order, GeoParquet metadata, no bloom filter, opens without extensions"],
    }  # fmt: skip


def main() -> int:
    manifest = json.loads((RAW / "MANIFEST.json").read_text())
    package = json.loads((RAW / "package.json").read_text())
    index, gs, cols, invalid, rows = facts()
    (DATA / "README.md").write_text(card_text(index, gs, cols, invalid, rows, manifest, package))
    (DATA / "LICENSE").write_text(license_text(index, rows))
    (DATA / "provenance.yaml").write_text(to_yaml(provenance(index, gs, rows, invalid, manifest, package)))
    print(f"card with {len(gs)} configs, {sum(rows.values()):,} rows")
    return 0


if __name__ == "__main__":
    sys.exit(main())

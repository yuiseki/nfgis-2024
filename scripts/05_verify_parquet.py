#!/usr/bin/env python3
"""Check the Parquet against the shapefiles in the zips.

For every source shapefile in data/parquet/2024/index.parquet:
  - attributes: the Parquet rows (by published name, NULLs dropped) hash to the digest of what
    GDAL reads from the same shapefile (data/work/gdal-digests.json, written by
    scripts/04_gdal_digests.py with a Python that has GDAL), and the row counts agree
  - geometry: each record's bounding box and number of points in the .shp record header equal
    the Parquet row's bbox and the number of points of its WKB; a record the Parquet lacks is
    a deleted DBF record or a failure, and the counts say which
  - the shapefiles of the zips are the ones of the index, and their counts add up
For every Parquet file: rows in (file_index, record) order; GeoParquet 1.1.0 metadata naming
geometry as the primary column, WKB, the CRS of its zone, the bbox of its rows and the bbox
covering; a DuckDB without extension autoloading opens it; no bloom filter.
Invalid geometries are counted and reported, not changed.

    uv run python scripts/05_verify_parquet.py
"""

import importlib.util
import json
import struct
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "2024"
PQ = ROOT / "data" / "parquet" / "2024"
DIGESTS = ROOT / "data" / "work" / "gdal-digests.json"


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).parent / file)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


export = _load("export", "03_export_parquet.py")
gd = _load("gd", "04_gdal_digests.py")
POLY, LINE = (5, 3)


def read_shp_records(data: bytes) -> dict[int, tuple[tuple[float, ...], int] | None]:
    """{record number (0 based): (bbox, number of points)} from the record headers."""
    out, pos, n = {}, 100, 0
    while pos + 8 <= len(data):
        _, words = struct.unpack(">2i", data[pos : pos + 8])
        body = data[pos + 8 : pos + 8 + words * 2]
        (kind,) = struct.unpack("<i", body[:4])
        if kind == 0:
            out[n] = None
        elif kind in (POLY, LINE):
            bbox = struct.unpack("<4d", body[4:36])
            _parts, npoints = struct.unpack("<2i", body[36:44])
            out[n] = (bbox, npoints)
        else:
            raise SystemExit(f"record {n}: shape type {kind} is not handled")
        pos += 8 + words * 2
        n += 1
    return out


def check_geo(geo: dict, epsg: int, extent: tuple[float, float, float, float]) -> list[str]:
    g = geo["columns"].get("geometry", {})
    bad = []
    if geo.get("version") != "1.1.0" or geo.get("primary_column") != "geometry":
        bad.append("version or primary column")
    if g.get("encoding") != "WKB":
        bad.append("encoding")
    if g.get("crs", {}).get("id") != {"authority": "EPSG", "code": epsg}:
        bad.append(f"crs is not EPSG:{epsg}")
    if [round(v, 6) for v in g.get("bbox", [])] != [round(v, 6) for v in extent]:
        bad.append("bbox is not the extent of the rows")
    if g.get("covering", {}).get("bbox", {}).get("xmin") != ["bbox", "xmin"]:
        bad.append("covering")
    return bad


def main() -> int:
    import duckdb

    failures = 0

    def check(ok: bool, what: str) -> None:
        nonlocal failures
        print(("ok   " if ok else "FAIL ") + what)
        failures += not ok

    con = duckdb.connect()
    con.execute("load spatial")
    con.execute("set enable_geoparquet_conversion = false")
    plain = duckdb.connect(config={"autoload_known_extensions": False,
                                   "autoinstall_known_extensions": False})  # fmt: skip
    if not DIGESTS.exists():
        print(f"FAIL {DIGESTS} missing: run scripts/04_gdal_digests.py with a Python that has GDAL")
        return 1
    gdal = json.loads(DIGESTS.read_text())
    index = con.sql(f"select source, layer, zone, epsg, rows, output from '{PQ / 'index.parquet'}'").fetchall()

    zips = sorted(RAW.glob("*.zip"))
    in_zips = set()
    for z in zips:
        with zipfile.ZipFile(z) as zf:
            in_zips |= {n for n in zf.namelist() if n.endswith(".shp")}
    check(in_zips == {r[0] for r in index} == set(gdal),
          f"the {len(in_zips)} shapefiles of the zips are the index's and GDAL's")

    # Parquet side
    by_file: dict[str, list[tuple]] = {}
    for r in index:
        by_file.setdefault(r[5], []).append(r)
    pq_rows: dict[str, tuple[int, str]] = {}
    geom: dict[str, dict] = {}
    invalid = 0
    for out, sources in sorted(by_file.items(), key=lambda kv: str(kv[0])):
        if out is None:
            check(all(r[4] == 0 for r in sources), f"{len(sources)} shapefile(s) without a file have no rows")
            continue
        p = PQ / out
        cols = [c for c in con.sql(f"select * from '{p}' limit 0").columns]
        attrs = [c for c in cols if c not in ("file_index", "record", "source", "geometry", "bbox")]
        sel = ", ".join(f'"{c}"' for c in attrs)
        lines: dict[str, list[str]] = {}
        ordered = con.sql(f"select source, record, {sel} from '{p}' order by file_index, record").fetchall()
        for src, _rec, *vals in ordered:
            lines.setdefault(src, []).append(gd.canonical(dict(zip(attrs, vals, strict=True))))
        for src, ls in lines.items():
            pq_rows[src] = gd.digest(ls)
        g = con.sql(
            f"select source, record, bbox.xmin, bbox.ymin, bbox.xmax, bbox.ymax, "
            f"ST_NPoints(ST_GeomFromWKB(geometry)) from '{p}'"
        ).fetchall()
        for src, rec, *rest in g:
            geom.setdefault(src, {})[rec] = (tuple(rest[:4]), rest[4])
        invalid += con.sql(
            f"select count(*) from '{p}' where geometry is not null and not ST_IsValid(ST_GeomFromWKB(geometry))"
        ).fetchone()[0]
        # structure
        sorted_ok = con.sql(
            f"select count(*) from (select file_index, record, lag(file_index) over w pf, lag(record) over w pr "
            f"from '{p}' window w as (order by file_index, record)) where pf is not null and (file_index, record) <= (pf, pr)"
        ).fetchone()[0]
        extent = con.sql(f"select min(bbox.xmin), min(bbox.ymin), max(bbox.xmax), max(bbox.ymax) from '{p}'").fetchone()
        geo = json.loads(con.sql(
            f"select decode(value) from parquet_kv_metadata('{p}') where decode(key) = 'geo'").fetchone()[0])  # fmt: skip
        bad = check_geo(geo, sources[0][3], extent)
        bloom = con.sql(f"select count(*) filter (where bloom_filter_offset is not null) from parquet_metadata('{p}')").fetchone()[0]
        n = plain.sql(f"select count(*) from '{p}'").fetchone()[0]
        check(not sorted_ok and not bad and bloom == 0 and n == sum(r[4] for r in sources),
              f"{out}: {n:,} rows, order, geo metadata ({bad or f'EPSG:{sources[0][3]}'}), no bloom, opens plain")

    # per source: attributes and geometry
    attr_bad, geom_bad, missing = [], [], 0
    for z in zips:
        with zipfile.ZipFile(z) as zf:
            for name in sorted(n for n in zf.namelist() if n.endswith(".shp")):
                rows, sha = pq_rows.get(name, (0, None))
                g = gdal[name]
                if (rows, sha) != (g["rows"], g["sha256"]) and not (rows == g["rows"] == 0):
                    attr_bad.append((name, rows, g["rows"]))
                recs = read_shp_records(zf.read(name))
                have = geom.get(name, {})
                missing += len(recs) - len(have)
                for rec, want in recs.items():
                    got = have.get(rec)
                    if want is None or got is None:
                        continue
                    (wb, wn), (gb, gn) = want, got
                    if wn != gn or any(abs(a - b) > 1e-6 for a, b in zip(wb, gb, strict=True)):
                        geom_bad.append((name, rec))
    check(not attr_bad, f"attributes of all {len(gdal)} shapefiles equal GDAL's ({attr_bad[:3] or 'none differ'})")
    check(not geom_bad, f"bbox and point count of every record equal the .shp header ({geom_bad[:3] or 'none differ'})")
    total = sum(r[4] for r in index)
    check(total == sum(g["rows"] for g in gdal.values()), f"{total:,} rows in all, as GDAL counts; {missing} .shp records without a row")
    print(f"note {invalid} invalid geometries (kept as published)")
    print("all ok" if not failures else f"{failures} failure(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

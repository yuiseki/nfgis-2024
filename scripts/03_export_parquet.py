#!/usr/bin/env python3
"""Turn the national forest shapefiles into one GeoParquet per layer and plane rectangular zone.

    data/parquet/2024/<layer>_zone<NN>.parquet   e.g. shouhan_zone09.parquet
    data/parquet/2024/index.parquet              one row per source shapefile (output is NULL
                                                 for a shapefile with no features: 林道 in
                                                 zones 14, 15, 16 and 19 are empty)

The 47 prefecture zips hold <prefecture>/<planning area>/第N系/<layer>.shp, 162 shapefiles per
layer in 17 zones (JGD2000 plane rectangular, EPSG:2443 to 2461). Coordinates are kept as
published, so a layer is split by zone, never reprojected. The three layers (小班区画 small
compartments, 林班区画 compartments, 林道 forest roads) are written to
shouhan_, rinpan_ and rindou_ files.

Each shapefile is read in two parts. The DBF is read here with the standard library: its field
names and values are Shift_JIS (code page 19), which the GDAL inside DuckDB does not decode. Its
field type gives the Parquet type (C text, N with no decimals BIGINT, N with decimals and F
DOUBLE); text is stripped and an empty text or number is NULL; a value that does not fit its
field stops the run. The geometry is read by DuckDB's ST_Read from a copy of the shapefile whose
DBF field names were replaced by ASCII, and joined to the attributes by record number; the zone
the directory names must be the zone the .prj declares. Rows are kept in file order: file_index
(the shapefile in the zip's name order), record (its DBF record number, 0 based).

Columns: file_index, record, source (path inside the zip), every attribute under its published
name (the union over the group, NULL where a shapefile lacks one; one name with two types stops
the run), geometry (WKB) and bbox (xmin, ymin, xmax, ymax of the geometry). The Parquet is
zstd compressed, written in row groups of 10,000 rows, with GeoParquet 1.1.0 metadata: WKB,
geometry types, the bounding box, the zone's CRS as PROJJSON and the bbox covering.

    uv run python scripts/03_export_parquet.py
    uv run python scripts/03_export_parquet.py --layer 林道 --zone 9
"""

import argparse
import csv
import json
import re
import shutil
import struct
import sys
import unicodedata
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "2024"
OUT = ROOT / "data" / "parquet" / "2024"
WORK = ROOT / "data" / "work"
LAYERS = {"小班区画": "shouhan", "林班区画": "rinpan", "林道": "rindou"}
CODE_PAGES = {19: "cp932"}  # the DBF language driver byte: 19 is Shift_JIS
ROW_GROUP_ROWS = 10_000
NUMBER = re.compile(r"-?\d+(\.\d+)?([eE][-+]?\d+)?")
INTEGER = re.compile(r"-?\d+")
GEO_TYPES = {"POINT": "Point", "LINESTRING": "LineString", "POLYGON": "Polygon",
             "MULTIPOINT": "MultiPoint", "MULTILINESTRING": "MultiLineString",
             "MULTIPOLYGON": "MultiPolygon"}  # fmt: skip
EXTS = ("shp", "shx", "dbf", "prj")


def zone_number(dirname: str) -> int:
    m = re.fullmatch(r"第(\d+)系", unicodedata.normalize("NFKC", dirname))
    if not m:
        raise SystemExit(f"{dirname!r} is not a zone directory (第N系)")
    return int(m.group(1))


def epsg_for_zone(zone: int) -> int:
    """JGD2000 plane rectangular coordinate system I to XIX is EPSG:2443 to 2461."""
    if not 1 <= zone <= 19:
        raise SystemExit(f"zone {zone} is not a plane rectangular zone (1 to 19)")
    return 2442 + zone


def prj_zone(prj: str) -> int | None:
    m = re.search(r"JGD_2000_Japan_Zone_(\d+)", prj)
    return int(m.group(1)) if m else None


def check_zone(zone_dir: str, prj: str) -> None:
    declared = prj_zone(prj)
    if declared != zone_number(zone_dir):
        raise SystemExit(f"{zone_dir}: the .prj declares zone {declared}")


def read_dbf_fields(data: bytes) -> tuple[list[tuple[str, str, int, int]], int, int, int]:
    """(fields, record count, header length, record length) from the DBF header."""
    nrec, hlen, rlen = struct.unpack("<IHH", data[4:12])
    code_page = CODE_PAGES.get(data[29])
    if code_page is None:
        raise SystemExit(f"DBF code page byte {data[29]}: only Shift_JIS (19) is handled")
    fields, i = [], 32
    while data[i] != 0x0D:
        name = data[i : i + 11].split(b"\0")[0].decode(code_page)
        kind, length, dec = chr(data[i + 11]), data[i + 16], data[i + 17]
        if kind == "C":
            sql = "VARCHAR"
        elif kind == "N":
            sql = "BIGINT" if dec == 0 else "DOUBLE"
        elif kind == "F":
            sql = "DOUBLE"
        else:
            raise SystemExit(f"{name}: DBF field type {kind!r} is not handled")
        fields.append((name, sql, length, dec))
        i += 32
    if len({f[0] for f in fields}) != len(fields):
        raise SystemExit("a DBF with two fields of one name")
    return fields, nrec, hlen, rlen


def read_dbf(data: bytes):
    """(fields, records): records yields (record number, values as text or None), deleted skipped."""
    fields, nrec, hlen, rlen = read_dbf_fields(data)
    if len(data) < hlen + nrec * rlen:
        raise SystemExit("the DBF is shorter than its header says")

    def records():
        for n in range(nrec):
            rec = data[hlen + n * rlen : hlen + (n + 1) * rlen]
            if rec[:1] == b"*":
                continue
            pos, values = 1, []
            for name, sql, length, _ in fields:
                raw = rec[pos : pos + length].decode("cp932").strip()
                pos += length
                if sql == "VARCHAR":
                    values.append(raw or None)
                    continue
                if not raw or set(raw) == {"*"}:
                    values.append(None)
                elif sql == "BIGINT" and INTEGER.fullmatch(raw):
                    values.append(str(int(raw)))
                elif sql == "DOUBLE" and NUMBER.fullmatch(raw):
                    values.append(repr(float(raw)))
                else:
                    raise SystemExit(f"{name}: {raw!r} is not a {sql} (record {n})")
            yield n, values

    return fields, records()


def plan_zips(zips: list[Path]) -> dict[tuple[str, int], list[dict]]:
    """Group the shapefiles of the zips by (layer, zone), each group in zip and name order."""
    plan: dict[tuple[str, int], list[dict]] = {}
    for z in zips:
        with zipfile.ZipFile(z) as zf:
            for name in sorted(zf.namelist()):
                if not name.endswith(".shp"):
                    continue
                parts = name.split("/")
                if len(parts) != 4:
                    raise SystemExit(f"{z.name}: unexpected path {name}")
                prefecture, area, zone_dir, file = parts
                layer = file[:-4]
                if layer not in LAYERS:
                    raise SystemExit(f"{z.name}: unknown layer {layer}")
                plan.setdefault((layer, zone_number(zone_dir)), []).append({
                    "zip": z, "base": name[:-4], "source": name, "prefecture": prefecture,
                    "area": area, "zone_dir": zone_dir, "layer": layer,
                })  # fmt: skip
    return plan


def sql_str(s: str) -> str:
    return s.replace("'", "''")


def ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def ascii_dbf(data: bytes) -> bytes:
    """The DBF with its field names replaced by f000, f001, ...: the records are untouched."""
    b = bytearray(data)
    i = k = 0
    i = 32
    while b[i] != 0x0D:
        b[i : i + 11] = f"f{k:03d}".encode().ljust(11, b"\0")
        i += 32
        k += 1
    return bytes(b)


def geo_metadata(types: list[str], extent: list[float], crs: dict) -> dict:
    return {
        "version": "1.1.0", "primary_column": "geometry",
        "columns": {"geometry": {
            "encoding": "WKB", "geometry_types": types, "crs": crs, "bbox": extent,
            "covering": {"bbox": {f: ["bbox", f] for f in ("xmin", "ymin", "xmax", "ymax")}},
        }},
    }  # fmt: skip


def export_group(layer: str, zone: int, sources: list[dict], out: Path, work: Path) -> dict:
    import duckdb

    epsg = epsg_for_zone(zone)
    schema: dict[str, str] = {}
    for s in sources:  # pass 1: every DBF header, for the union of the attributes
        with zipfile.ZipFile(s["zip"]) as zf, zf.open(s["base"] + ".dbf") as f:
            fields, *_ = read_dbf_fields(f.read(65536))
        for name, sql, *_ in fields:
            if schema.setdefault(name, sql) != sql:
                raise SystemExit(f"{name}: {schema[name]} in one shapefile, {sql} in {s['source']}")
    con = duckdb.connect()
    con.execute("load spatial")
    con.execute("set enable_geoparquet_conversion = false")
    con.execute("set memory_limit = '16GB'")
    attr_ddl = ", ".join(f"{ident(n)} {t}" for n, t in schema.items())
    con.execute(
        "create table t (file_index INTEGER, record BIGINT, source VARCHAR, "
        f"{attr_ddl}, geometry BLOB, "
        "bbox STRUCT(xmin DOUBLE, ymin DOUBLE, xmax DOUBLE, ymax DOUBLE))"
    )
    shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True)
    per_source = []
    for i, s in enumerate(sources):
        with zipfile.ZipFile(s["zip"]) as zf:
            parts = {e: zf.read(f"{s['base']}.{e}") for e in EXTS}
        check_zone(s["zone_dir"], parts["prj"].decode("ascii", "replace"))
        fields, records = read_dbf(parts["dbf"])
        (work / "s.shp").write_bytes(parts["shp"])
        (work / "s.shx").write_bytes(parts["shx"])
        (work / "s.prj").write_bytes(parts["prj"])
        (work / "s.dbf").write_bytes(ascii_dbf(parts["dbf"]))
        n = 0
        with open(work / "s.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["record"] + [f"f{k:03d}" for k in range(len(fields))])
            for rec, values in records:
                w.writerow([rec] + ["" if v is None else v for v in values])
                n += 1
        names = {name: f"f{k:03d}" for k, (name, *_) in enumerate(fields)}
        sel = ", ".join(
            f"CAST(a.{names[name]} AS {sql}) AS {ident(name)}" if name in names
            else f"CAST(NULL AS {sql}) AS {ident(name)}"
            for name, sql in schema.items()
        )
        cols = ", ".join(f"{c} VARCHAR" if c != "record" else "record BIGINT"
                         for c in ["record"] + list(names.values()))
        con.execute(f"""
            INSERT INTO t BY NAME
            SELECT {i} AS file_index, g.OGC_FID AS record, '{sql_str(s["source"])}' AS source,
                   {sel}, ST_AsWKB(g.geom) AS geometry,
                   CASE WHEN g.geom IS NULL THEN NULL ELSE struct_pack(
                     xmin := ST_XMin(ST_Extent(g.geom)), ymin := ST_YMin(ST_Extent(g.geom)),
                     xmax := ST_XMax(ST_Extent(g.geom)), ymax := ST_YMax(ST_Extent(g.geom))) END
                   AS bbox
            FROM ST_Read('{sql_str(str(work / "s.shp"))}') g
            JOIN read_csv('{sql_str(str(work / "s.csv"))}', header = true, all_varchar = true,
                          columns = {{{", ".join(f"'{c.split()[0]}': '{c.split()[1]}'" for c in cols.split(", "))}}}) a
              ON a.record = g.OGC_FID
        """)
        got = con.sql(f"select count(*) from t where file_index = {i}").fetchone()[0]
        total = con.sql(f"select count(*) from ST_Read('{sql_str(str(work / 's.shp'))}')").fetchone()[0]
        if not got == n == total:
            raise SystemExit(f"{s['source']}: {n} DBF records, {total} shapes, {got} joined")
        per_source.append({"source": s["source"], "prefecture": s["prefecture"],
                           "planning_area": s["area"], "rows": got})  # fmt: skip
    shutil.rmtree(work, ignore_errors=True)
    rows = con.sql("select count(*) from t").fetchone()[0]
    if rows == 0:  # no geometry, no bbox: nothing to put in the GeoParquet metadata
        return {"rows": 0, "epsg": epsg, "files": len(sources), "written": False,
                "geometry_types": [], "extent": None, "per_source": per_source,
                "columns": list(schema)}  # fmt: skip

    found = con.sql(
        "select distinct upper(ST_GeometryType(ST_GeomFromWKB(geometry))::VARCHAR), "
        "ST_HasZ(ST_GeomFromWKB(geometry)) from t where geometry is not null"
    ).fetchall()
    types = sorted(GEO_TYPES[t] + (" Z" if z else "") for t, z in found)
    extent = list(con.sql(
        "select min(bbox.xmin), min(bbox.ymin), max(bbox.xmax), max(bbox.ymax) from t"
    ).fetchone())  # fmt: skip
    row = con.sql("select projjson from duckdb_coordinate_systems() "
                  f"where auth_name = 'EPSG' and auth_code = '{epsg}'").fetchone()
    if row is None:
        raise SystemExit(f"EPSG:{epsg} is not in DuckDB's PROJ database")
    geo = geo_metadata(types, extent, json.loads(row[0]))
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_name(out.name + ".part")
    con.execute(f"""
        COPY (SELECT * FROM t ORDER BY file_index, record) TO '{sql_str(str(tmp))}'
        (FORMAT parquet, COMPRESSION zstd, WRITE_BLOOM_FILTER false, ROW_GROUP_SIZE {ROW_GROUP_ROWS},
         KV_METADATA {{geo: '{sql_str(json.dumps(geo))}'}})
    """)
    tmp.replace(out)
    return {"rows": rows, "epsg": epsg, "files": len(sources), "written": True,
            "geometry_types": types,
            "extent": extent, "per_source": per_source, "columns": list(schema)}  # fmt: skip


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", choices=list(LAYERS))
    ap.add_argument("--zone", type=int)
    a = ap.parse_args()
    plan = plan_zips(sorted(RAW.glob("*.zip")))
    if not plan:
        raise SystemExit(f"no zip under {RAW}; run scripts/01_download.py")
    order = {n: i for i, n in enumerate(LAYERS)}
    index = []
    for (layer, zone), sources in sorted(plan.items(), key=lambda kv: (order[kv[0][0]], kv[0][1])):
        if (a.layer and layer != a.layer) or (a.zone and zone != a.zone):
            continue
        out = OUT / f"{LAYERS[layer]}_zone{zone:02d}.parquet"
        info = export_group(layer, zone, sources, out, WORK / f"{LAYERS[layer]}_{zone}")
        if info["written"]:
            print(f"{out.name}: {info['rows']:,} rows from {info['files']} shapefiles, "
                  f"EPSG:{info['epsg']}, {out.stat().st_size:,} bytes", flush=True)  # fmt: skip
        else:
            out.unlink(missing_ok=True)
            print(f"{out.name}: no rows in {info['files']} shapefile(s), not written", flush=True)
        index += [{**r, "layer": layer, "zone": zone, "epsg": info["epsg"],
                   "output": out.name if info["written"] else None}
                  for r in info["per_source"]]  # fmt: skip
    if not (a.layer or a.zone):
        write_index(index)
    return 0


def write_index(index: list[dict]) -> None:
    import duckdb

    con = duckdb.connect()
    con.execute("create table i (source VARCHAR, prefecture VARCHAR, planning_area VARCHAR, "
                "layer VARCHAR, zone INTEGER, epsg INTEGER, rows BIGINT, output VARCHAR)")
    con.executemany("insert into i values (?, ?, ?, ?, ?, ?, ?, ?)",
                    [[r["source"], r["prefecture"], r["planning_area"], r["layer"], r["zone"],
                      r["epsg"], r["rows"], r["output"]] for r in index])  # fmt: skip
    OUT.mkdir(parents=True, exist_ok=True)
    con.execute(f"copy (select * from i order by source) to '{sql_str(str(OUT / 'index.parquet'))}' "
                "(format parquet, compression zstd)")
    print(f"index.parquet: {len(index)} shapefiles")


if __name__ == "__main__":
    sys.exit(main())

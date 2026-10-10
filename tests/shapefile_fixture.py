"""A minimal shapefile writer for tests: Polygon or PolyLine records, a DBF in Shift_JIS."""

import struct
import zipfile
from pathlib import Path

PRJ = (
    'PROJCS["JGD_2000_Japan_Zone_{z}",GEOGCS["GCS_JGD_2000",DATUM["D_JGD_2000",'
    'SPHEROID["GRS_1980",6378137.0,298.257222101]],PRIMEM["Greenwich",0.0],'
    'UNIT["Degree",0.0174532925199433]],PROJECTION["Transverse_Mercator"],'
    'PARAMETER["False_Easting",0.0],PARAMETER["False_Northing",0.0],'
    'PARAMETER["Central_Meridian",139.8333333333333],PARAMETER["Scale_Factor",0.9999],'
    'PARAMETER["Latitude_Of_Origin",36.0],UNIT["Meter",1.0]]'
)


def _record(kind: int, rings: list[list[tuple[float, float]]]) -> bytes:
    pts = [p for r in rings for p in r]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    parts, n = [], 0
    for r in rings:
        parts.append(n)
        n += len(r)
    body = struct.pack("<i4d2i", kind, min(xs), min(ys), max(xs), max(ys), len(rings), len(pts))
    body += struct.pack(f"<{len(parts)}i", *parts)
    body += b"".join(struct.pack("<2d", *p) for p in pts)
    return body


def shapefile(records, fields, rows, zone: int, kind: int = 5, ldid: int = 19) -> dict[str, bytes]:
    """records: list of ring lists; fields: [(name, type, length, decimals)]; rows: lists of str."""
    shp_body, shx_body, offset = b"", b"", 50
    for i, rings in enumerate(records, 1):
        rec = _record(kind, rings)
        words = len(rec) // 2
        shp_body += struct.pack(">2i", i, words) + rec
        shx_body += struct.pack(">2i", offset, words)
        offset += 4 + words
    allpts = [p for rings in records for r in rings for p in r] or [(0.0, 0.0)]
    box = (min(p[0] for p in allpts), min(p[1] for p in allpts),
           max(p[0] for p in allpts), max(p[1] for p in allpts))  # fmt: skip

    def header(length_words):
        return struct.pack(">7i", 9994, 0, 0, 0, 0, 0, length_words) + struct.pack(
            "<2i8d", 1000, kind, *box, 0, 0, 0, 0)

    shp = header(50 + len(shp_body) // 2) + shp_body
    shx = header(50 + len(shx_body) // 2) + shx_body
    rlen = 1 + sum(f[2] for f in fields)
    hlen = 32 + 32 * len(fields) + 1
    dbf = struct.pack("<4BIHH", 3, 26, 10, 10, len(rows), hlen, rlen) + b"\0" * 17
    dbf += bytes([ldid]) + b"\0\0"
    for name, t, length, dec in fields:
        dbf += name.encode("cp932").ljust(11, b"\0") + t.encode() + b"\0" * 4
        dbf += bytes([length, dec]) + b"\0" * 14
    dbf += b"\r"
    for row in rows:
        deleted = row[0] == "*"
        cells = row[1:] if deleted else row
        dbf += b"*" if deleted else b" "
        for (_name, t, length, _dec), v in zip(fields, cells, strict=True):
            raw = v.encode("cp932")
            dbf += raw.rjust(length) if t in "NF" else raw.ljust(length)
    dbf += b"\x1a"
    return {"shp": shp, "shx": shx, "dbf": dbf, "prj": PRJ.format(z=zone).encode()}


def add_to_zip(zf: zipfile.ZipFile, base: str, files: dict[str, bytes]) -> None:
    for ext, data in files.items():
        zf.writestr(f"{base}.{ext}", data)


def write_zip(path: Path, members: dict[str, dict[str, bytes]]) -> Path:
    """members: {"13東京都/48多摩森林計画区/第9系/小班区画": shapefile(...)}"""
    with zipfile.ZipFile(path, "w") as zf:
        for base, files in members.items():
            add_to_zip(zf, base, files)
    return path

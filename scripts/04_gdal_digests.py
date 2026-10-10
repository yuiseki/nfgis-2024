#!/usr/bin/env python3
"""Read every shapefile of the zips with GDAL and write a digest of its attributes.

An independent reader for scripts/05_verify_parquet.py: GDAL decodes the Shift_JIS DBF itself
(SHAPE_ENCODING=CP932), unlike the code that wrote the Parquet. For each shapefile it counts
the features and hashes, in record order, one canonical line per feature: the attributes that
are not NULL, by published name, as sorted JSON (text stripped, empty text NULL, numbers as
GDAL reads them, the six characters iconv and Microsoft decode differently in Microsoft's form,
see MS_FORMS). Needs a Python with GDAL (osgeo), which uv's environment does not have:

    /home/yuiseki/anaconda3/bin/python scripts/04_gdal_digests.py

Writes data/work/gdal-digests.json: {source path in the zip: {"rows": n, "sha256": "..."}}.
"""

import hashlib
import json
import os
import sys
import warnings
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "2024"
OUT = ROOT / "data" / "work" / "gdal-digests.json"


# GDAL decodes Shift_JIS with iconv's CP932, which maps six two-byte codes to the JIS X 0208
# characters; the Parquet uses Python's cp932 (Microsoft), which maps them to the full-width
# forms. The GDAL strings are put in Microsoft's forms so the two readers can be compared:
# 0x817C - 0x8160 ~ 0x8161 ||  0x8191 cent  0x8192 pound  0x81CA not
MS_FORMS = str.maketrans({"\u2212": "\uff0d", "\u301c": "\uff5e", "\u2016": "\u2225",
                          "\u00a2": "\uffe0", "\u00a3": "\uffe1", "\u00ac": "\uffe2"})  # fmt: skip


def ms_form(v):
    return v.translate(MS_FORMS) if isinstance(v, str) else v


def norm(v):
    if isinstance(v, str):
        return v.strip() or None
    return v


def canonical(attrs: dict) -> str:
    return json.dumps({k: norm(v) for k, v in sorted(attrs.items()) if norm(v) is not None},
                      ensure_ascii=False, sort_keys=True)


def digest(lines) -> tuple[int, str]:
    h, n = hashlib.sha256(), 0
    for line in lines:
        h.update(line.encode() + b"\n")
        n += 1
    return n, h.hexdigest()


def main() -> int:
    os.environ["SHAPE_ENCODING"] = "CP932"
    warnings.filterwarnings("ignore", category=FutureWarning)
    from osgeo import gdal, ogr

    gdal.UseExceptions()
    ogr.UseExceptions()
    result = {}
    for z in sorted(RAW.glob("*.zip")):
        with zipfile.ZipFile(z) as zf:
            shps = sorted(n for n in zf.namelist() if n.endswith(".shp"))
        for name in shps:
            ds = ogr.Open(f"/vsizip/{z}/{name}")
            layer = ds.GetLayer(0)
            defn = layer.GetLayerDefn()
            fields = [defn.GetFieldDefn(i).GetName() for i in range(defn.GetFieldCount())]
            lines = (canonical({fields[i]: ms_form(f.GetField(i)) for i in range(len(fields))})
                     for f in layer)  # fmt: skip
            n, sha = digest(lines)
            result[name] = {"rows": n, "sha256": sha}
        print(f"{z.name}: {len(shps)} shapefiles", flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

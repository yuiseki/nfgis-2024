# nfgis-2024

The national forest GIS data (国有林GISデータ), 2024 edition, of Japan's Forestry Agency
(林野庁): the small compartment (小班区画), compartment (林班区画) and forest road (林道)
layers of the national forests, as shapefiles per prefecture, with the specification, the
code table and the terms. Reference date 2024-04-01.

- Official source: the G-Spatial Information Center CKAN, <https://www.geospatial.jp/ckan/dataset/nfgis-2024>
  (publisher 林野庁 国有林野部 経営企画課).
- Licence: the Public Data License 1.0 (PDL1.0, compatible with CC BY 4.0) with the Forestry
  Agency's own notes: credit the source as "出典：国有林 GIS データ（当該ページの URL）、PDL1.0",
  say so when you edit or process the data, and do not present the result as made by the
  Forestry Agency. The CKAN record names the licence `ol` (own terms), which is the
  "公共データ利用規約（第1.0版）に関する重要情報" PDF in the files. The "留意事項" PDF warns that the
  positions and areas do not always match the ground and that the data was made for the
  Agency's administrative work.
- Layout: 47 prefecture zips; inside, 都道府県 / 森林計画区 / 第N系 (plane rectangular zone) /
  layer.shp. 486 shapefiles, 17 zones (JGD2000, EPSG:2443 to 2461), no .cpg file.

## Run

```sh
uv run python scripts/01_download.py --dry-run     # the plan and its size (about 1.4 GB)
uv run python scripts/01_download.py               # fetch; run again to resume
uv run python scripts/02_verify.py                 # sizes, sha256, zips, PDFs against the manifest
uv run python scripts/03_export_parquet.py         # shapefiles -> data/parquet/2024/ (GeoParquet)
/home/yuiseki/anaconda3/bin/python scripts/04_gdal_digests.py   # GDAL's reading, for the check
uv run python scripts/05_verify_parquet.py         # Parquet against GDAL and the .shp headers
uv run python scripts/06_card.py                   # data/README.md, LICENSE, provenance.yaml
uv run python src/publish.py                       # dry run; --push uploads to the Hub
uv run python -m pytest
```

`04_gdal_digests.py` needs a Python with GDAL (osgeo), which uv's environment does not have.
`06_card.py` needs `pdftotext` (poppler) to quote the terms PDFs.

`01_download.py` reads the file list from the CKAN API (saved as `data/raw/2024/package.json`),
fetches one file at a time, one second apart, writes `.part` files and resumes them with Range.
Most catalogue URLs carry a `www.geospatial.jp` prefix on the file name that the server answers
with HTTP 500; the name without it delivers the file with the size the catalogue states, so it is
tried next. The server is slow (50 KB/s to 1 MB/s per connection).

`data/` is not tracked except the card, `LICENSE` and `provenance.yaml`; the files are under
`data/raw/2024/` with a `MANIFEST.json`, and the Parquet under `data/parquet/2024/`.

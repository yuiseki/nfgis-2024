---
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
- config_name: 'index'
  data_files: parquet/2024/index.parquet
  default: true
- config_name: 'shouhan_zone01'
  data_files: parquet/2024/shouhan_zone01.parquet
- config_name: 'shouhan_zone02'
  data_files: parquet/2024/shouhan_zone02.parquet
- config_name: 'shouhan_zone03'
  data_files: parquet/2024/shouhan_zone03.parquet
- config_name: 'shouhan_zone04'
  data_files: parquet/2024/shouhan_zone04.parquet
- config_name: 'shouhan_zone05'
  data_files: parquet/2024/shouhan_zone05.parquet
- config_name: 'shouhan_zone06'
  data_files: parquet/2024/shouhan_zone06.parquet
- config_name: 'shouhan_zone07'
  data_files: parquet/2024/shouhan_zone07.parquet
- config_name: 'shouhan_zone08'
  data_files: parquet/2024/shouhan_zone08.parquet
- config_name: 'shouhan_zone09'
  data_files: parquet/2024/shouhan_zone09.parquet
- config_name: 'shouhan_zone10'
  data_files: parquet/2024/shouhan_zone10.parquet
- config_name: 'shouhan_zone11'
  data_files: parquet/2024/shouhan_zone11.parquet
- config_name: 'shouhan_zone12'
  data_files: parquet/2024/shouhan_zone12.parquet
- config_name: 'shouhan_zone13'
  data_files: parquet/2024/shouhan_zone13.parquet
- config_name: 'shouhan_zone14'
  data_files: parquet/2024/shouhan_zone14.parquet
- config_name: 'shouhan_zone15'
  data_files: parquet/2024/shouhan_zone15.parquet
- config_name: 'shouhan_zone16'
  data_files: parquet/2024/shouhan_zone16.parquet
- config_name: 'shouhan_zone19'
  data_files: parquet/2024/shouhan_zone19.parquet
- config_name: 'rinpan_zone01'
  data_files: parquet/2024/rinpan_zone01.parquet
- config_name: 'rinpan_zone02'
  data_files: parquet/2024/rinpan_zone02.parquet
- config_name: 'rinpan_zone03'
  data_files: parquet/2024/rinpan_zone03.parquet
- config_name: 'rinpan_zone04'
  data_files: parquet/2024/rinpan_zone04.parquet
- config_name: 'rinpan_zone05'
  data_files: parquet/2024/rinpan_zone05.parquet
- config_name: 'rinpan_zone06'
  data_files: parquet/2024/rinpan_zone06.parquet
- config_name: 'rinpan_zone07'
  data_files: parquet/2024/rinpan_zone07.parquet
- config_name: 'rinpan_zone08'
  data_files: parquet/2024/rinpan_zone08.parquet
- config_name: 'rinpan_zone09'
  data_files: parquet/2024/rinpan_zone09.parquet
- config_name: 'rinpan_zone10'
  data_files: parquet/2024/rinpan_zone10.parquet
- config_name: 'rinpan_zone11'
  data_files: parquet/2024/rinpan_zone11.parquet
- config_name: 'rinpan_zone12'
  data_files: parquet/2024/rinpan_zone12.parquet
- config_name: 'rinpan_zone13'
  data_files: parquet/2024/rinpan_zone13.parquet
- config_name: 'rinpan_zone14'
  data_files: parquet/2024/rinpan_zone14.parquet
- config_name: 'rinpan_zone15'
  data_files: parquet/2024/rinpan_zone15.parquet
- config_name: 'rinpan_zone16'
  data_files: parquet/2024/rinpan_zone16.parquet
- config_name: 'rinpan_zone19'
  data_files: parquet/2024/rinpan_zone19.parquet
- config_name: 'rindou_zone01'
  data_files: parquet/2024/rindou_zone01.parquet
- config_name: 'rindou_zone02'
  data_files: parquet/2024/rindou_zone02.parquet
- config_name: 'rindou_zone03'
  data_files: parquet/2024/rindou_zone03.parquet
- config_name: 'rindou_zone04'
  data_files: parquet/2024/rindou_zone04.parquet
- config_name: 'rindou_zone05'
  data_files: parquet/2024/rindou_zone05.parquet
- config_name: 'rindou_zone06'
  data_files: parquet/2024/rindou_zone06.parquet
- config_name: 'rindou_zone07'
  data_files: parquet/2024/rindou_zone07.parquet
- config_name: 'rindou_zone08'
  data_files: parquet/2024/rindou_zone08.parquet
- config_name: 'rindou_zone09'
  data_files: parquet/2024/rindou_zone09.parquet
- config_name: 'rindou_zone10'
  data_files: parquet/2024/rindou_zone10.parquet
- config_name: 'rindou_zone11'
  data_files: parquet/2024/rindou_zone11.parquet
- config_name: 'rindou_zone12'
  data_files: parquet/2024/rindou_zone12.parquet
- config_name: 'rindou_zone13'
  data_files: parquet/2024/rindou_zone13.parquet
---

# nfgis-2024

The national forest GIS data (国有林GISデータ), 2024 edition, of Japan's Forestry Agency
(林野庁): the small compartments (小班区画, 975,666 polygons), the compartments
(林班区画, 58,293 polygons) and the forest roads (林道, 57,912 lines) of the
national forests, in the shapefiles the Agency publishes and as GeoParquet. Reference date
2024-04-01, forest plans up to FY2023 (令和5年度).

- Official source: the G-Spatial Information Center,
  <https://www.geospatial.jp/ckan/dataset/nfgis-2024> (publisher 林野庁 国有林野部 経営企画課,
  published 2025-12, record last modified 2026-02-24).
- Licence: the Public Data License 1.0 (PDL1.0, compatible with CC BY 4.0); see Licence.
- Code: <https://github.com/yuiseki/nfgis-2024> (download, verify, export, card).

## What is here

| path | what |
|---|---|
| `raw/2024/` | the 51 files of the CKAN package, unchanged: 47 prefecture zips of shapefiles, the specification, the code table, the two terms PDFs; `MANIFEST.json` (URL, size, sha256, fetch time) and `package.json` (the catalogue record) |
| `parquet/2024/` | one GeoParquet per layer and zone, and `index.parquet` |

The files were fetched 2026-10-09 to 2026-10-10. This dataset is the 2024 edition; a later
edition would be added beside it, not over it.

## The shapefiles and how the Parquet is split

Each prefecture zip holds `<prefecture>/<forest planning area>/第N系/<layer>.shp`:
486 shapefiles (47 prefectures, 158 planning areas) in 17 zones of the
JGD2000 plane rectangular coordinate system. A zone is a coordinate system, so the Parquet
is split by layer and zone and the coordinates are exactly as published, never reprojected.
Each file carries the CRS of its zone (EPSG:2443 for 第1系 up to EPSG:2461 for 第19系) in its
GeoParquet metadata. `index.parquet` has one row per source shapefile (`source`, `prefecture`,
`planning_area`, `layer`, `zone`, `epsg`, `rows`, `output`).

| file | layer | zone | CRS | shapefiles | rows |
|---|---|---|---|---:|---:|
| `shouhan_zone01.parquet` | 小班区画 small compartments | 第1系 | EPSG:2443 | 5 | 6,518 |
| `shouhan_zone02.parquet` | 小班区画 small compartments | 第2系 | EPSG:2444 | 23 | 109,684 |
| `shouhan_zone03.parquet` | 小班区画 small compartments | 第3系 | EPSG:2445 | 12 | 15,636 |
| `shouhan_zone04.parquet` | 小班区画 small compartments | 第4系 | EPSG:2446 | 12 | 19,844 |
| `shouhan_zone05.parquet` | 小班区画 small compartments | 第5系 | EPSG:2447 | 9 | 15,194 |
| `shouhan_zone06.parquet` | 小班区画 small compartments | 第6系 | EPSG:2448 | 17 | 16,842 |
| `shouhan_zone07.parquet` | 小班区画 small compartments | 第7系 | EPSG:2449 | 11 | 28,293 |
| `shouhan_zone08.parquet` | 小班区画 small compartments | 第8系 | EPSG:2450 | 16 | 77,532 |
| `shouhan_zone09.parquet` | 小班区画 small compartments | 第9系 | EPSG:2451 | 20 | 128,714 |
| `shouhan_zone10.parquet` | 小班区画 small compartments | 第10系 | EPSG:2452 | 17 | 267,771 |
| `shouhan_zone11.parquet` | 小班区画 small compartments | 第11系 | EPSG:2453 | 3 | 56,966 |
| `shouhan_zone12.parquet` | 小班区画 small compartments | 第12系 | EPSG:2454 | 9 | 158,240 |
| `shouhan_zone13.parquet` | 小班区画 small compartments | 第13系 | EPSG:2455 | 3 | 72,464 |
| `shouhan_zone14.parquet` | 小班区画 small compartments | 第14系 | EPSG:2456 | 1 | 911 |
| `shouhan_zone15.parquet` | 小班区画 small compartments | 第15系 | EPSG:2457 | 2 | 426 |
| `shouhan_zone16.parquet` | 小班区画 small compartments | 第16系 | EPSG:2458 | 1 | 627 |
| `shouhan_zone19.parquet` | 小班区画 small compartments | 第19系 | EPSG:2461 | 1 | 4 |
| `rinpan_zone01.parquet` | 林班区画 compartments | 第1系 | EPSG:2443 | 5 | 303 |
| `rinpan_zone02.parquet` | 林班区画 compartments | 第2系 | EPSG:2444 | 23 | 4,303 |
| `rinpan_zone03.parquet` | 林班区画 compartments | 第3系 | EPSG:2445 | 12 | 1,094 |
| `rinpan_zone04.parquet` | 林班区画 compartments | 第4系 | EPSG:2446 | 12 | 1,780 |
| `rinpan_zone05.parquet` | 林班区画 compartments | 第5系 | EPSG:2447 | 9 | 1,055 |
| `rinpan_zone06.parquet` | 林班区画 compartments | 第6系 | EPSG:2448 | 17 | 1,429 |
| `rinpan_zone07.parquet` | 林班区画 compartments | 第7系 | EPSG:2449 | 11 | 2,914 |
| `rinpan_zone08.parquet` | 林班区画 compartments | 第8系 | EPSG:2450 | 16 | 8,208 |
| `rinpan_zone09.parquet` | 林班区画 compartments | 第9系 | EPSG:2451 | 20 | 4,607 |
| `rinpan_zone10.parquet` | 林班区画 compartments | 第10系 | EPSG:2452 | 17 | 10,953 |
| `rinpan_zone11.parquet` | 林班区画 compartments | 第11系 | EPSG:2453 | 3 | 6,298 |
| `rinpan_zone12.parquet` | 林班区画 compartments | 第12系 | EPSG:2454 | 9 | 11,046 |
| `rinpan_zone13.parquet` | 林班区画 compartments | 第13系 | EPSG:2455 | 3 | 4,073 |
| `rinpan_zone14.parquet` | 林班区画 compartments | 第14系 | EPSG:2456 | 1 | 40 |
| `rinpan_zone15.parquet` | 林班区画 compartments | 第15系 | EPSG:2457 | 2 | 78 |
| `rinpan_zone16.parquet` | 林班区画 compartments | 第16系 | EPSG:2458 | 1 | 111 |
| `rinpan_zone19.parquet` | 林班区画 compartments | 第19系 | EPSG:2461 | 1 | 1 |
| `rindou_zone01.parquet` | 林道 forest roads | 第1系 | EPSG:2443 | 5 | 516 |
| `rindou_zone02.parquet` | 林道 forest roads | 第2系 | EPSG:2444 | 23 | 6,972 |
| `rindou_zone03.parquet` | 林道 forest roads | 第3系 | EPSG:2445 | 12 | 1,853 |
| `rindou_zone04.parquet` | 林道 forest roads | 第4系 | EPSG:2446 | 12 | 4,031 |
| `rindou_zone05.parquet` | 林道 forest roads | 第5系 | EPSG:2447 | 9 | 1,515 |
| `rindou_zone06.parquet` | 林道 forest roads | 第6系 | EPSG:2448 | 17 | 1,672 |
| `rindou_zone07.parquet` | 林道 forest roads | 第7系 | EPSG:2449 | 11 | 3,529 |
| `rindou_zone08.parquet` | 林道 forest roads | 第8系 | EPSG:2450 | 16 | 7,325 |
| `rindou_zone09.parquet` | 林道 forest roads | 第9系 | EPSG:2451 | 20 | 5,250 |
| `rindou_zone10.parquet` | 林道 forest roads | 第10系 | EPSG:2452 | 17 | 10,731 |
| `rindou_zone11.parquet` | 林道 forest roads | 第11系 | EPSG:2453 | 3 | 2,549 |
| `rindou_zone12.parquet` | 林道 forest roads | 第12系 | EPSG:2454 | 9 | 7,090 |
| `rindou_zone13.parquet` | 林道 forest roads | 第13系 | EPSG:2455 | 3 | 4,879 |

Shapefiles with no features have no Parquet file; `index.parquet` lists them with 0 rows and
`output` NULL:

- `13東京都/49伊豆諸島森林計画区/第14系/林道.shp`
- `13東京都/49伊豆諸島森林計画区/第19系/林道.shp`
- `47沖縄県/156沖縄北部森林計画区/第15系/林道.shp`
- `47沖縄県/157沖縄中南部森林計画区/第15系/林道.shp`
- `47沖縄県/158宮古八重山森林計画区/第16系/林道.shp`

## Columns

Every file starts with `file_index` (the shapefile's position in the group, by its path in the
zip), `record` (its DBF record number, 0 based) and `source` (the path inside the zip), then the
attributes under their published names, then `geometry` (WKB) and `bbox` (a struct xmin, ymin,
xmax, ymax of the geometry, the GeoParquet 1.1 covering). All shapefiles of a layer have the same
attributes. Types are the DBF field types: text is VARCHAR (also the digit strings such as
the ID, which keep their leading zeros), a number with no decimals BIGINT, a number with decimals
DOUBLE. Text is stripped of spaces and an empty text or number is NULL.

`shouhan_zone*.parquet` (小班区画, 975,666 rows, 4,325 invalid geometries):

| column | type | meaning |
|---|---|---|
| `ID` | VARCHAR | identifier: digits of the codes below, zero padded (23 digits for a small compartment, 19 for a compartment, 14 for a road) |
| `森林管理局` | VARCHAR | forest management bureau code |
| `森林管理署` | VARCHAR | forest office code |
| `林班主番` | VARCHAR | compartment number |
| `林班枝番` | VARCHAR | compartment branch number (0 if none) |
| `小班主番` | VARCHAR | small compartment number |
| `小班枝番` | VARCHAR | small compartment branch number (0 if none) |
| `局名称` | VARCHAR | bureau name |
| `署名称` | VARCHAR | office name |
| `小班名` | VARCHAR | small compartment name |
| `林小班名称` | VARCHAR | combined compartment and small compartment name |
| `材積` | BIGINT | timber volume of the small compartment, m3 |
| `国有林名` | VARCHAR | national forest name |
| `担当区` | VARCHAR | district |
| `県市町村` | VARCHAR | municipality |
| `樹種１` | VARCHAR | tree species with the largest area share |
| `樹立林齢１` | VARCHAR | its age when the forest plan was made |
| `樹種２` | VARCHAR | second largest species |
| `樹立林齢２` | VARCHAR | its age |
| `樹種３` | VARCHAR | third largest species |
| `樹立林齢３` | VARCHAR | its age |
| `計画区` | VARCHAR | forest planning area |
| `林種の細分` | VARCHAR | forest type (e.g. 天 natural forest, 単 single-layer plantation) |
| `機能類型` | VARCHAR | function to be emphasised |
| `面積` | DOUBLE | area of the small compartment, ha |
| `保安林１` | VARCHAR | protection forest type 1 |
| `保安林２` | VARCHAR | type 2 |
| `保安林３` | VARCHAR | type 3 |
| `保安林４` | VARCHAR | type 4 |
| `保護林` | VARCHAR | code of the protected forest it is set in |
| `緑の回廊` | VARCHAR | code of the green corridor |
| `樹立年度` | VARCHAR | fiscal year of the forest plan |

`rinpan_zone*.parquet` (林班区画, 58,293 rows, 293 invalid geometries):

| column | type | meaning |
|---|---|---|
| `ID` | VARCHAR | identifier: digits of the codes below, zero padded (23 digits for a small compartment, 19 for a compartment, 14 for a road) |
| `森林管理局` | VARCHAR | forest management bureau code |
| `森林管理署` | VARCHAR | forest office code |
| `林班主番` | VARCHAR | compartment number |
| `林班枝番` | VARCHAR | compartment branch number (0 if none) |
| `局名称` | VARCHAR | bureau name |
| `署名称` | VARCHAR | office name |

`rindou_zone*.parquet` (林道, 57,912 rows, 0 invalid geometries):

| column | type | meaning |
|---|---|---|
| `ID` | VARCHAR | identifier: digits of the codes below, zero padded (23 digits for a small compartment, 19 for a compartment, 14 for a road) |
| `森林管理局` | VARCHAR | forest management bureau code |
| `森林管理署` | VARCHAR | forest office code |
| `路線番号` | VARCHAR | road route number |
| `林道名` | VARCHAR | road name |

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
- 4,618 geometries are not valid by the OGC rules (4,325 small
  compartments, 293 compartments, 0 roads). They are kept as
  published; fix them (for example with ST_MakeValid) before computing with them.
- `樹立林齢１` to `樹立林齢３` and `樹立年度` are text in the DBF and stay text here.
- The specification says each data unit is a forest planning area ("データ単位 森林計画区"); a
  planning area on islands in more than one zone (for example 49伊豆諸島森林計画区, zones 9, 14
  and 19) has a shapefile per zone, so it appears in more than one Parquet file.

## Checked before upload

`scripts/05_verify_parquet.py` checks, for all 486 source shapefiles:

- every attribute of every feature (1,091,871 in all) equals what GDAL
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

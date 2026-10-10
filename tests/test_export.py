import importlib.util
import json
from pathlib import Path

import duckdb
import pytest
from shapefile_fixture import shapefile, write_zip

HERE = Path(__file__).parent
_spec = importlib.util.spec_from_file_location("ex", HERE.parent / "scripts" / "03_export_parquet.py")
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)

SQ = [[(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]]
SQ2 = [[(20.0, 20.0), (30.0, 20.0), (30.0, 30.0), (20.0, 30.0), (20.0, 20.0)]]
FIELDS = [("ID", "C", 8, 0), ("局名称", "C", 10, 0), ("材積", "N", 6, 0), ("面積", "F", 12, 4)]
ROWS = [["A1", "関東", "   120", "   10.5000"], ["A2", "", "     0", "    1.2500"]]


def test_zone_number_reads_ordinary_and_full_width_digits():
    assert m.zone_number("第9系") == 9
    assert m.zone_number("第６系") == 6
    assert m.zone_number("第14系") == 14
    with pytest.raises(SystemExit, match="zone"):
        m.zone_number("北海道")


def test_epsg_of_a_jgd2000_zone():
    assert [m.epsg_for_zone(z) for z in (1, 9, 19)] == [2443, 2451, 2461]
    with pytest.raises(SystemExit, match="zone"):
        m.epsg_for_zone(20)


def test_the_prj_zone_is_read_and_must_match_the_directory():
    f = shapefile([SQ], FIELDS, ROWS[:1], zone=9)
    assert m.prj_zone(f["prj"].decode()) == 9
    with pytest.raises(SystemExit, match="第10系"):
        m.check_zone("第10系", f["prj"].decode())


def test_dbf_names_values_and_types_are_read_in_shift_jis():
    f = shapefile([SQ, SQ2], FIELDS, ROWS, zone=9)
    fields, records = m.read_dbf(f["dbf"])
    assert [(n, t, d) for n, t, _, d in fields] == [
        ("ID", "VARCHAR", 0), ("局名称", "VARCHAR", 0), ("材積", "BIGINT", 0), ("面積", "DOUBLE", 4)]  # fmt: skip
    recs = list(records)
    assert recs[0] == (0, ["A1", "関東", "120", "10.5"])
    assert recs[1] == (1, ["A2", None, "0", "1.25"])


def test_a_deleted_record_is_skipped_and_the_others_keep_their_index():
    rows = [ROWS[0], ["*"] + ROWS[1]]
    f = shapefile([SQ, SQ2], FIELDS, rows, zone=9)
    _, records = m.read_dbf(f["dbf"])
    assert [i for i, _ in records] == [0]


def test_an_unknown_field_type_or_code_page_stops():
    f = shapefile([SQ], [("日付", "D", 8, 0)], [["20240401"]], zone=9)
    with pytest.raises(SystemExit, match="field type"):
        m.read_dbf(f["dbf"])
    f = shapefile([SQ], FIELDS, ROWS[:1], zone=9, ldid=87)
    with pytest.raises(SystemExit, match="code page"):
        m.read_dbf(f["dbf"])


def test_a_number_that_does_not_fit_its_field_stops():
    f = shapefile([SQ], [("材積", "N", 6, 0)], [["    1x2"]], zone=9)
    with pytest.raises(SystemExit, match="材積"):
        list(m.read_dbf(f["dbf"])[1])


def build(tmp_path, second_fields=None):
    a = shapefile([SQ, SQ2], FIELDS, ROWS, zone=9)
    f2 = second_fields or FIELDS
    b = shapefile([SQ2], f2, [["B1", "近畿", "   7", "    2.0000"][: len(f2)]], zone=9)
    c = shapefile([SQ], FIELDS, ROWS[:1], zone=2)
    write_zip(tmp_path / "13東京都.zip", {
        "13東京都/48多摩森林計画区/第9系/小班区画": a,
        "13東京都/49伊豆諸島森林計画区/第9系/小班区画": b,
        "13東京都/49伊豆諸島森林計画区/第2系/小班区画": c,
    })  # fmt: skip
    return tmp_path


def test_plan_groups_shapefiles_by_layer_and_zone_in_file_order(tmp_path):
    raw = build(tmp_path)
    plan = m.plan_zips(sorted(raw.glob("*.zip")))
    assert list(plan) == [("小班区画", 9), ("小班区画", 2)]
    assert [s["area"] for s in plan[("小班区画", 9)]] == ["48多摩森林計画区", "49伊豆諸島森林計画区"]
    assert plan[("小班区画", 9)][0]["prefecture"] == "13東京都"


def test_a_group_is_written_as_geoparquet_with_the_zones_crs(tmp_path):
    raw = build(tmp_path)
    plan = m.plan_zips(sorted(raw.glob("*.zip")))
    out = tmp_path / "out.parquet"
    info = m.export_group("小班区画", 9, plan[("小班区画", 9)], out, tmp_path / "work")
    con = duckdb.connect()
    con.execute("set enable_geoparquet_conversion = false")
    cols = con.sql(f"select * from '{out}'").columns
    assert cols == ["file_index", "record", "source", "ID", "局名称", "材積", "面積", "geometry", "bbox"]
    rows = con.sql(f'select record, source, "ID", "局名称", "材積", "面積" from \'{out}\'').fetchall()
    assert rows == [
        (0, "13東京都/48多摩森林計画区/第9系/小班区画.shp", "A1", "関東", 120, 10.5),
        (1, "13東京都/48多摩森林計画区/第9系/小班区画.shp", "A2", None, 0, 1.25),
        (0, "13東京都/49伊豆諸島森林計画区/第9系/小班区画.shp", "B1", "近畿", 7, 2.0),
    ]
    assert info["rows"] == 3 and info["epsg"] == 2451
    bb = con.sql(f"select bbox.xmin, bbox.ymin, bbox.xmax, bbox.ymax from '{out}'").fetchall()
    assert bb[0] == (0.0, 0.0, 10.0, 10.0) and bb[2] == (20.0, 20.0, 30.0, 30.0)
    wkb = con.sql(f"select ST_AsText(ST_GeomFromWKB(geometry)) from '{out}' limit 1").fetchone()[0]
    assert wkb.startswith("POLYGON")
    geo = json.loads(con.sql(
        f"select decode(value) from parquet_kv_metadata('{out}') where decode(key) = 'geo'"
    ).fetchone()[0])  # fmt: skip
    g = geo["columns"]["geometry"]
    assert geo["version"] == "1.1.0" and geo["primary_column"] == "geometry"
    assert g["geometry_types"] == ["Polygon"] and g["bbox"] == [0.0, 0.0, 30.0, 30.0]
    assert g["crs"]["id"] == {"authority": "EPSG", "code": 2451}
    assert g["covering"]["bbox"]["xmin"] == ["bbox", "xmin"]


def test_attributes_one_area_lacks_are_null_in_the_union(tmp_path):
    raw = build(tmp_path, second_fields=FIELDS[:3])
    plan = m.plan_zips(sorted(raw.glob("*.zip")))
    out = tmp_path / "out.parquet"
    m.export_group("小班区画", 9, plan[("小班区画", 9)], out, tmp_path / "work")
    con = duckdb.connect()
    con.execute("set enable_geoparquet_conversion = false")
    assert con.sql(f'select "面積" from \'{out}\' order by file_index, record').fetchall() == [
        (10.5,), (1.25,), (None,)]  # fmt: skip


def test_one_name_with_two_types_in_a_group_stops(tmp_path):
    raw = build(tmp_path, second_fields=[FIELDS[0], FIELDS[1], ("材積", "C", 6, 0), FIELDS[3]])
    plan = m.plan_zips(sorted(raw.glob("*.zip")))
    with pytest.raises(SystemExit, match="材積"):
        m.export_group("小班区画", 9, plan[("小班区画", 9)], tmp_path / "o.parquet", tmp_path / "w")


def test_a_zone_directory_that_disagrees_with_the_prj_stops(tmp_path):
    a = shapefile([SQ], FIELDS, ROWS[:1], zone=10)
    write_zip(tmp_path / "x.zip", {"13東京都/48多摩/第9系/小班区画": a})
    plan = m.plan_zips([tmp_path / "x.zip"])
    with pytest.raises(SystemExit, match="第9系"):
        m.export_group("小班区画", 9, plan[("小班区画", 9)], tmp_path / "o.parquet", tmp_path / "w")


def test_gdal_and_parquet_canonical_lines_agree_on_what_they_drop():
    spec = importlib.util.spec_from_file_location("gd", HERE.parent / "scripts" / "04_gdal_digests.py")
    gd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gd)
    line = gd.canonical({"b": " x ", "a": 3, "c": "", "d": None, "e": 1.5})
    assert line == '{"a": 3, "b": "x", "e": 1.5}'
    assert gd.digest(["a", "b"]) == gd.digest(iter(["a", "b"]))
    assert gd.digest(["a"])[0] == 1


def test_a_group_of_empty_shapefiles_writes_no_file_and_is_still_counted(tmp_path):
    empty = shapefile([], FIELDS, [], zone=14)
    write_zip(tmp_path / "x.zip", {"13東京都/49伊豆諸島森林計画区/第14系/林道": empty})
    plan = m.plan_zips([tmp_path / "x.zip"])
    out = tmp_path / "o.parquet"
    info = m.export_group("林道", 14, plan[("林道", 14)], out, tmp_path / "w")
    assert info["rows"] == 0 and info["written"] is False and not out.exists()
    assert info["per_source"][0]["rows"] == 0


def _verify_module():
    spec = importlib.util.spec_from_file_location("vp", HERE.parent / "scripts" / "05_verify_parquet.py")
    vp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(vp)
    return vp


def test_shp_record_headers_give_bbox_and_point_count():
    f = shapefile([SQ, SQ2], FIELDS, ROWS, zone=9)
    recs = _verify_module().read_shp_records(f["shp"])
    assert recs == {0: ((0.0, 0.0, 10.0, 10.0), 5), 1: ((20.0, 20.0, 30.0, 30.0), 5)}


def test_geo_metadata_check_names_what_is_wrong():
    vp = _verify_module()
    good = {"version": "1.1.0", "primary_column": "geometry", "columns": {"geometry": {
        "encoding": "WKB", "bbox": [0, 0, 1, 1], "covering": {"bbox": {"xmin": ["bbox", "xmin"]}},
        "crs": {"id": {"authority": "EPSG", "code": 2451}}}}}  # fmt: skip
    assert vp.check_geo(good, 2451, (0, 0, 1, 1)) == []
    assert vp.check_geo(good, 2452, (0, 0, 1, 1)) == ["crs is not EPSG:2452"]
    assert vp.check_geo(good, 2451, (0, 0, 1, 2)) == ["bbox is not the extent of the rows"]


def test_gdal_strings_are_put_in_microsofts_cp932_forms_for_the_six_characters_that_differ():
    spec = importlib.util.spec_from_file_location("gd2", HERE.parent / "scripts" / "04_gdal_digests.py")
    gd = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gd)
    # 0x817C 0x8160 0x8161 0x8191 0x8192 0x81CA: iconv gives the JIS X 0208 characters,
    # Python's cp932 the Microsoft ones
    iconv = "\u2212\u301c\u2016\u00a2\u00a3\u00ac"
    ms = bytes([0x81, 0x7C, 0x81, 0x60, 0x81, 0x61, 0x81, 0x91, 0x81, 0x92, 0x81, 0xCA]).decode("cp932")
    assert iconv != ms and gd.ms_form(iconv) == ms
    assert gd.ms_form("ペペシュ−ル") == "ペペシュ－ル" and gd.ms_form(5) == 5


def test_the_parquet_is_written_without_bloom_filters(tmp_path):
    raw = build(tmp_path)
    plan = m.plan_zips(sorted(raw.glob("*.zip")))
    out = tmp_path / "o.parquet"
    m.export_group("小班区画", 9, plan[("小班区画", 9)], out, tmp_path / "w")
    n = duckdb.connect().sql(
        f"select count(*) filter (where bloom_filter_offset is not null) from parquet_metadata('{out}')"
    ).fetchone()[0]
    assert n == 0

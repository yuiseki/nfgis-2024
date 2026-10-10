import importlib.util
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

HERE = Path(__file__).parent
_spec = importlib.util.spec_from_file_location("dl", HERE.parent / "scripts" / "01_download.py")
m = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(m)

CKAN = {
    "result": {
        "id": "450dcc55",
        "resources": [
            {"id": "r0", "format": "URL", "name": "公共データ利用規約（第1.0版）",
             "url": "https://www.digital.go.jp/resources/open_data/public_data_license_v1.0",
             "size": None},
            {"id": "r1", "format": "PDF", "name": "国有林GISデータ仕様書.pdf",
             "url": "https://example.test/dl/gis.pdf", "size": 155792},
            {"id": "r2", "format": "PDF", "name": "国有林GISデータの利用に当たっての留意事項",
             "url": "https://example.test/dl/gis2.pdf", "size": 158242},
            {"id": "r3", "format": "ZIP", "name": "01北海道.zip",
             "url": "https://example.test/dl/01.zip", "size": 452837825},
        ],
    }
}


def test_ckan_plan_skips_links_and_gives_every_file_an_extension():
    plan = m.ckan_plan(CKAN)
    assert [p["name"] for p in plan] == [
        "国有林GISデータ仕様書.pdf", "国有林GISデータの利用に当たっての留意事項.pdf", "01北海道.zip",
    ]
    assert plan[2]["bytes"] == 452_837_825 and plan[2]["resource_id"] == "r3"
    assert [lk["url"] for lk in m.ckan_links(CKAN)] == [
        "https://www.digital.go.jp/resources/open_data/public_data_license_v1.0"
    ]


def test_two_resources_with_one_name_stop():
    dup = json.loads(json.dumps(CKAN))
    dup["result"]["resources"][2]["name"] = "国有林GISデータ仕様書.pdf"
    with pytest.raises(SystemExit, match="same file name"):
        m.ckan_plan(dup)


@pytest.mark.parametrize("name", ["../x.zip", "a/b.zip", "a\\b.zip", "", ".", "..", "a\x00b"])
def test_unsafe_file_names_are_refused(name):
    with pytest.raises(SystemExit, match="unsafe"):
        m.safe_name(name)


BODY = bytes(range(256)) * 400  # 102,400 bytes


class Handler(BaseHTTPRequestHandler):
    truncate = False

    def log_message(self, *a):
        pass

    def do_GET(self):
        if "www.geospatial.jp" in self.path or "always500" in self.path:
            self.send_response(500)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        rng = self.headers.get("Range")
        start = 0
        if rng:
            start = int(rng.split("=")[1].split("-")[0])
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{len(BODY) - 1}/{len(BODY)}")
        else:
            self.send_response(200)
        data = BODY[start:]
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Last-Modified", "Wed, 01 Oct 2026 00:00:00 GMT")
        self.end_headers()
        self.wfile.write(data[: len(data) // 2] if Handler.truncate else data)


@pytest.fixture
def server():
    s = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=s.serve_forever, daemon=True).start()
    Handler.truncate = False
    yield f"http://127.0.0.1:{s.server_port}/f.bin"
    s.shutdown()


def test_fetch_writes_the_file_with_its_hash(server, tmp_path):
    e = m.fetch(server, tmp_path / "f.bin")
    assert (tmp_path / "f.bin").read_bytes() == BODY
    assert e["bytes"] == len(BODY) and len(e["sha256"]) == 64
    assert e["last_modified"] == "Wed, 01 Oct 2026 00:00:00 GMT"
    assert not (tmp_path / "f.bin.part").exists()


def test_fetch_resumes_a_part_file_and_hashes_the_whole(server, tmp_path):
    (tmp_path / "f.bin.part").write_bytes(BODY[:50_000])
    e = m.fetch(server, tmp_path / "f.bin")
    assert (tmp_path / "f.bin").read_bytes() == BODY
    assert e["sha256"] == m.sha256_file(tmp_path / "f.bin")


def test_a_short_answer_leaves_the_part_file_and_fails(server, tmp_path):
    Handler.truncate = True
    with pytest.raises(m.Incomplete):
        m.fetch(server, tmp_path / "f.bin")
    assert not (tmp_path / "f.bin").exists()
    assert (tmp_path / "f.bin.part").stat().st_size == len(BODY) // 2


def test_a_file_the_manifest_already_has_is_not_fetched(tmp_path):
    f = tmp_path / "a.zip"
    f.write_bytes(b"abc")
    entry = {"url": "https://x/a.zip", "bytes": 3, "sha256": m.sha256_file(f)}
    assert m.is_current(tmp_path / "a.zip", entry, "https://x/a.zip")
    assert not m.is_current(tmp_path / "a.zip", entry, "https://x/other.zip")
    fell_back = {**entry, "url": "https://x/stripped/a.zip", "catalogue_url": "https://x/a.zip"}
    assert m.is_current(tmp_path / "a.zip", fell_back, "https://x/a.zip")
    f.write_bytes(b"abd")
    assert not m.is_current(tmp_path / "a.zip", entry, "https://x/a.zip")
    assert not m.is_current(tmp_path / "missing.zip", entry, "https://x/a.zip")


def test_candidates_strip_the_prefix_the_catalogue_adds_to_file_names():
    url = "https://x/ckan/dataset/d/resource/r/download/www.geospatial.jp01.zip"
    assert m.candidates(url) == [url, "https://x/ckan/dataset/d/resource/r/download/01.zip"]
    plain = "https://x/ckan/dataset/d/resource/r/download/25.zip"
    assert m.candidates(plain) == [plain]


def test_a_500_on_the_catalogue_url_falls_back_to_the_stripped_one(server, tmp_path):
    base = server.rsplit("/", 1)[0]
    e = m.fetch_with_retries(f"{base}/dl/www.geospatial.jpf.bin", tmp_path / "f.bin")
    assert (tmp_path / "f.bin").read_bytes() == BODY
    assert e["url"] == f"{base}/dl/f.bin"


def test_a_file_both_urls_refuse_is_reported_as_failed(server, tmp_path):
    base = server.rsplit("/", 1)[0]
    with pytest.raises(m.Failed, match="HTTP 500"):
        m.fetch_with_retries(f"{base}/dl/www.geospatial.jpalways500", tmp_path / "x.bin")
    assert not (tmp_path / "x.bin").exists()

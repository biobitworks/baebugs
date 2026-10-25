import json
import re

from baebugs import labware_twin as lt


def test_committed_bundle_verifies():
    r = lt.verify()
    assert r["ok"], r["fails"]
    assert r["fragments"] > 200


def test_tamper_is_caught(tmp_path):
    import shutil
    shutil.copytree(lt.OUT, tmp_path / "lw")
    stl = tmp_path / "lw" / "stl" / "print-honeycomb.stl"
    stl.write_bytes(stl.read_bytes() + b"x")
    r = lt.verify(tmp_path / "lw")
    assert not r["ok"] and r["fails"] == ["file stl/print-honeycomb.stl"]


def test_remixes_are_centered_and_printable():
    for p in lt.PRINTS:
        q = p["params"]
        if "pitch" in q:
            assert abs(q["a1_x"] - (q["footprint_x"] - (q["cols"] - 1) * q["pitch"]) / 2) < 0.01, p["id"]
            assert abs(q["a1_y"] - (q["footprint_y"] - (q["rows"] - 1) * q["pitch"]) / 2) < 0.01, p["id"]
            # SBS racks keep 1.2 mm webs; the 133 mm cryo grid is pitch-bound and gets one 0.4 mm nozzle line
            assert q["pitch"] - q["hole_d"] >= (1.2 if p["ot"] else 0.4 - 1e-9), p["id"]
        if p["ot"]:
            assert (q["footprint_x"], q["footprint_y"]) == (lt.SBS_X, lt.SBS_Y)
            d = lt.opentrons_def(p)
            assert len(d["wells"]) == q["rows"] * q["cols"]
            assert d["wells"]["A1"]["y"] > d["wells"][f"{'ABCDEFGHIJKLMNOP'[q['rows'] - 1]}1"]["y"]   # A1 at back


def test_hash_rules_are_stable():
    assert lt.canon({"b": 9.0, "a": [1.5, 2.0]}) == '{"a":[1.5,2],"b":9}'
    assert lt.merkle(["00" * 32])[0] == "00" * 32
    t = lt.tree([("b", 1), ("a", 2), ("c", 3)])
    assert [f["name"] for f in t["fragments"]] == ["a", "b", "c"]
    assert all(lt.climb(f["leaf"], f["proof"]) == t["root"] for f in t["fragments"])


def test_no_vendor_marks_and_estimates_flagged():
    text = (lt.OUT / "catalog.json").read_text() + json.dumps(lt.OBSERVED)
    for f in (lt.OUT / "opentrons").glob("*.json"):
        text += f.read_text()
    banned = r"biotix|xtip|kashi|\bvwr\b|avantor|biologix|greiner|cryo\.s|helix"
    assert not re.search(banned, text, re.IGNORECASE)
    assert all(p["dims"]["est"] for p in lt.OBSERVED if p["kind"] != "reference")
    assert len(json.loads((lt.OUT / "merkle" / "breaks.json").read_text())) == len(lt.PHOTOS)

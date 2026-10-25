from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"site/mvp"))
from build_public_site import build, H

def test_workflow_main_page_has_truthful_stage_and_twin():
    s=(ROOT/"site/mvp/index.html").read_text()
    for stage in ["intake","sort","disperse","pick","plate","evidence"]:
        assert 'data-stage="'+stage+'"' in s
    assert s.count('id="p-workflow"')==1
    assert 'src="../twin/"' in s
    assert 'data-twin-view="lab"' in s
    assert "NOT_TESTED" in s
    assert 'source(s); access requires original consent' in s

def test_packaging_keeps_twin_and_labware_with_no_person_photos():
    with TemporaryDirectory() as d:
        from pathlib import Path
        root=Path(d)/"site"
        m=build(root,"0"*40)
        assert m["source_ref"]=="0"*40
        for f in ["index.html","mvp.json","twin/index.html","lab/index.html",
                  "lab/lab.js","lab/parts.json","print/labware/previews.png","bench_observation.json"]:
            assert f in m["files"], f
            assert H(root/f)==m["files"][f]["sha256"]
        assert "source_ref" in (root/"deployment-manifest.json").read_text()
        assert "photos" not in [x.parent.name for x in root.rglob("*.jpg")]
        assert json.loads((root/"mvp.json").read_text())["root"]==m["evidence_pack_root"]

def test_virtual_twin_metrics_are_explicitly_simulated():
    twin=(ROOT/"site/twin/index.html").read_text()
    assert "Virtual checks pass" in twin
    assert "modeled recovery, not measured" in twin
    assert "specimens recovered</span>" not in twin

def test_private_photo_record_never_bundles_source_pixels():
    import json
    note=json.loads((ROOT/"docs/bench/bench_photo_observation_20261025.json").read_text())
    assert note["source"]["public_source_bytes"]=="WITHHELD"
    assert note["source"]["publication_consent"]=="UNKNOWN"
    assert len(note["source"]["sha256_exact_file_bytes"])==64

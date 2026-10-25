"""Deterministically stage Baebugs MVP root, bench twin, CAD/STL viewer and labware.

Derived deployment files are not a new Merkle root; the included source pack
remains pinned and separately validated by repo source identity.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

REPO = Path(__file__).resolve().parents[2]

def H(path: Path) -> str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(1024*1024),b''):
            h.update(b)
    return h.hexdigest()

def build(target: Path, source_ref: str):
    if not re.fullmatch(r"[0-9a-f]{40}", source_ref):
        raise ValueError("Source revision must be a full verified Git commit SHA")
    target=target.resolve()
    if target == REPO or REPO in target.parents:
        raise ValueError("Output must be outside repository to avoid evidence recursion")
    target.mkdir(parents=True, exist_ok=True)
    html=(REPO/"site/mvp/index.html").read_text()
    marker="const BASE = new URL('../../', location.href);"
    assert html.count(marker)==1
    html=html.replace(marker,
        "const BASE = new URL('https://raw.githubusercontent.com/biobitworks/baebugs/"+source_ref+"/');")
    assert 'id="workflow-twin"' in html
    assert 'id="p-workflow"' in html
    (target/"index.html").write_text(html)
    shutil.copy2(REPO/"site/mvp/mvp.json",target/"mvp.json")
    shutil.copy2(REPO/"docs/bench/bench_photo_observation_20261025.json",target/"bench_observation.json")
    for rel in ["site/lab","site/twin","site/protocols"]:
        d=target/Path(rel).name
        if d.exists(): shutil.rmtree(d)
        shutil.copytree(REPO/rel,d,ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    # Public protocols are source-verified derived projections, not execution proof.
    import sys
    sys.path.insert(0, str(REPO / "site/protocols"))
    from build_catalog import build as compile_protocols
    resolved = compile_protocols(REPO, target/"mvp.json")
    resolved["source_commit"] = source_ref
    (target/"protocols/catalog.json").write_text(
        json.dumps(resolved, indent=2, ensure_ascii=False, sort_keys=True)+chr(10))
    # The 3D labware preview and Opentrons schemas linked by the Parts tab.
    for rel in ["print/labware/previews.png"]:
        dest=target/rel;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(REPO/rel,dest)
    sh=REPO/"print/labware/opentrons"
    if sh.exists():
        d=target/"print/labware/opentrons"
        if d.exists(): shutil.rmtree(d)
        shutil.copytree(sh,d)
    # Do not package source photos withheld for licensing or consent.
    assert not (target/"assets/photos").exists()
    (target/"robots.txt").write_text("User-agent: *\nAllow: /\n")
    files={}
    for p in sorted(target.rglob("*")):
        if p.is_file() and p.name!="deployment-manifest.json" and not any(x.startswith(".") for x in p.relative_to(target).parts):
            files[p.relative_to(target).as_posix()]={"sha256":H(p),"bytes":p.stat().st_size}
    manifest={"schema":"baebugs.portal.deployment-manifest.v1",
              "source_ref":source_ref,"evidence_pack_root":json.loads((target/"mvp.json").read_text())["root"],
              "status":"DERIVED_DEPLOYMENT_PACKAGE", "signed":"NOT_SIGNED",
              "files":files,"included_people_photos":False,
              "reproduces_physical_robot_execution":False}
    (target/"deployment-manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    return manifest

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--ref",required=True)
    args=ap.parse_args()
    m=build(args.out,args.ref)
    print(json.dumps({"root":m["evidence_pack_root"],"file_count":len(m["files"]),
                      "manifest_sha256":H(args.out/"deployment-manifest.json"),"staged_to":str(args.out)}))
if __name__=="__main__":main()

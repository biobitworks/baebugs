"""Retention policy: what must be kept, what is regenerable (proven by rebuild +
hash), what is droppable. Nothing is deleted here: the output is a plan with
reclaimable bytes (hardlink-aware) and a proof root appended to the impact MMR.

Classes
  KEEP         irreplaceable or non-reproducible: frozen truths/protocols, MMRs and
               ledgers, raw source photos, teacher pseudo-labels, model answers,
               one weights file per behaviour class, ruler truth sets
  REGENERABLE  rebuilt from specs and checked byte-for-byte by sha256 (proof leaf);
               safe to drop and rebuild on demand
  DROPPABLE    duplicates, failed or stopped realizations (their hashes stay in the MMR),
               staging copies re-creatable from verified manifests
A REGENERABLE class whose rebuild does not match is demoted to KEEP (and reported).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from pathlib import Path

from .explore import merkle_root


def sha(p, chunk=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def size_info(paths):
    """bytes on disk and bytes actually reclaimable (files with a single link)."""
    tot = rec = n = 0
    for p in paths:
        for f in ([p] if Path(p).is_file() else Path(p).rglob("*")):
            if f.is_file() and not f.is_symlink():
                st = f.stat(); tot += st.st_size; n += 1
                if st.st_nlink == 1:
                    rec += st.st_size
    return {"files": n, "bytes": tot, "reclaimable_bytes": rec}


def compare_dirs(original, rebuilt, pattern="*"):
    o = {str(p.relative_to(original)): p for p in Path(original).rglob(pattern) if p.is_file()}
    r = {str(p.relative_to(rebuilt)): p for p in Path(rebuilt).rglob(pattern) if p.is_file()}
    common = sorted(set(o) & set(r))
    mism = [k for k in common if sha(o[k]) != sha(r[k])]
    return {"compared": len(common), "missing_in_rebuild": sorted(set(o) - set(r))[:5],
            "n_missing": len(set(o) - set(r)), "mismatch": mism[:5], "n_mismatch": len(mism),
            "proven": len(common) > 0 and not mism and not (set(o) - set(r)),
            "root": merkle_root(sorted(sha(o[k]) for k in common))}


# ---------------------------------------------------------------- proofs

def prove_print_toys(repo="."):
    from .printmodels import generate
    with tempfile.TemporaryDirectory() as t:
        generate(t)
        return compare_dirs(Path(repo, "print/fuse1"), t, "*.stl") | {"what": "91 toy STLs + 2 trees"}


def prove_scad(repo="."):
    from .scad_export import export
    with tempfile.TemporaryDirectory() as t:
        shutil.copy2(Path(repo, "print/fuse1/manifest.csv"), Path(t, "manifest.csv"))
        export(t, Path(t, "filters"))
        return compare_dirs(Path(repo, "print/fuse1/scad"), Path(t, "scad"), "*.scad") | {"what": "toy OpenSCAD"}


def prove_filters(repo="."):
    from .punch_filters import build
    with tempfile.TemporaryDirectory() as t:
        build(t)
        return compare_dirs(Path(repo, "print/filters/stl"), Path(t, "stl"), "*.stl") | {"what": "filter plate STLs"}


def prove_toy_kg(repo="."):
    from .insect_kg import build_collection
    with tempfile.TemporaryDirectory() as t:
        build_collection(Path(repo, "print/fuse1/manifest.csv"), t)
        return compare_dirs(Path(repo, "print/fuse1/kg/insects"), Path(t, "insects"), "*.json") | {"what": "toy Merkle KG trees"}


def prove_multires(data_root, n=25):
    """Re-resample n pseudo images at each MP level and compare bytes."""
    import cv2
    from .resolution import at_megapixels
    src = Path(data_root, "pseudo_specimens_r3_real/images")
    out = {"compared": 0, "n_mismatch": 0, "mismatch": []}
    for lvl, d in (("0.3", 0.3), ("1", 1.0), ("3", 3.0)):
        mdir = Path(data_root, f"multires_r4_multires/mp_{lvl}/images")
        files = sorted(mdir.glob("*/*.jpg"))[:n]
        for f in files:
            img = cv2.imread(str(src / f.parent.name / f.name))
            ok, buf = cv2.imencode(".jpg", at_megapixels(img, d)[0], [cv2.IMWRITE_JPEG_QUALITY, 92])
            out["compared"] += 1
            if hashlib.sha256(buf.tobytes()).hexdigest() != sha(f):
                out["n_mismatch"] += 1; out["mismatch"].append(str(f.relative_to(data_root)))
    out["mismatch"] = out["mismatch"][:5]
    out["proven"] = out["compared"] > 0 and out["n_mismatch"] == 0
    out["what"] = f"multires resamples (sample {n}/level)"
    return out


def prove_toy_renders(render_root, n=20):
    import cv2
    from .model_compare import render
    files = sorted(Path(render_root).rglob("*.png"))[:n]
    idx = {}
    for kg in (Path("print/fuse1/kg/index.json"),):
        if kg.exists():
            idx = {x["name"]: x for x in json.loads(kg.read_text())}
    out = {"compared": 0, "n_mismatch": 0, "mismatch": []}
    for f in files:
        x = idx.get(f.stem)
        if not x:
            continue
        ppm = float(f.parent.name.replace("ppm", ""))
        ok, buf = cv2.imencode(".png", render(x["length_mm"], x["plan"], ppm))
        out["compared"] += 1
        if hashlib.sha256(buf.tobytes()).hexdigest() != sha(f):
            out["n_mismatch"] += 1; out["mismatch"].append(f.name)
    out["mismatch"] = out["mismatch"][:5]
    out["proven"] = out["compared"] > 0 and out["n_mismatch"] == 0
    out["what"] = f"toy renders (sample {n})"
    return out


# ---------------------------------------------------------------- plans

def repo_plan(repo="."):
    R = Path(repo)
    items = []
    for name, paths, fn in (("toy STLs", [R / "print/fuse1/california", R / "print/fuse1/novel_outside_ca",
                                          R / "print/fuse1/fill_in_1-3mm", R / "print/fuse1/trees"], prove_print_toys),
                            ("toy OpenSCAD", [R / "print/fuse1/scad"], prove_scad),
                            ("filter STLs", [R / "print/filters/stl"], prove_filters),
                            ("toy KG trees", [R / "print/fuse1/kg/insects"], prove_toy_kg)):
        if not all(p.exists() for p in paths):
            continue
        proof = fn(repo)
        items.append({"name": name, "class": "REGENERABLE" if proof["proven"] else "KEEP",
                      "paths": [str(p) for p in paths], **size_info(paths), "proof": proof})
    keep = [("frozen truth + protocols", ["daisy/TRUTH-001.json", *map(str, R.glob("daisy/DAISY-BB-*.json"))]),
            ("MMRs + ledgers", [*map(str, R.glob("daisy/*mmr.jsonl")), "ledger"]),
            ("model answers (attestation sources)", ["print/fuse1/kg/compare", "print/fuse1/kg/lomo", "print/fuse1/kg/triage"])]
    for name, paths in keep:
        ps = [R / p for p in paths if (R / p).exists()]
        items.append({"name": name, "class": "KEEP", "paths": [str(p) for p in ps], **size_info(ps)})
    return items


def drive_plan(base="/Volumes/magicBLACKbox/baebugs", lab="/Volumes/magicLABbox/baebugs"):
    B, D = Path(base), Path(base, "datasets")
    items = []
    def add(name, cls, paths, reason, proof=None):
        ps = [Path(p) for p in paths if Path(p).exists()]
        if ps:
            items.append({"name": name, "class": cls, "reason": reason, "paths": [str(p) for p in ps], **size_info(ps),
                          **({"proof": proof} if proof else {})})
    add("raw GBIF photos", "KEEP", [D / "gbif_ca_2", D / "gbif_az", D / "gbif_nv", D / "gbif_or", Path(lab, "datasets/gbif_specimen_images")],
        "source data (re-downloadable, not reproducible)")
    add("teacher pseudo-labels", "KEEP", [D / "pseudo_specimens_r3_real"], "model outputs: costly to recompute")
    add("ruler truth sets", "KEEP", [D / "_teacher_check", D / "_teacher_check2"], "truth")
    mp = prove_multires(D)
    add("multires resamples", "REGENERABLE" if mp["proven"] else "KEEP", [D / "multires_r4_multires"],
        "rebuild with resolution.at_megapixels from pseudo-labels", mp)
    add("synthetic sets", "KEEP", [D / "synth_1_30_r2", D / "synth_1_30_r3_real"], "seeded but not yet proven by full rebuild")
    add("rejected pseudo v1", "DROPPABLE", [D / "_rejected_pseudo_v1"], "negative record: keep its DAISY manifest + root, drop images")
    add("Kaggle staging bundles", "DROPPABLE", [B / "daisy/kaggle"], "hardlinked/copied from verified datasets; re-stage from manifests")
    rr = prove_toy_renders(B / "daisy/derived/toy_renders") if (B / "daisy/derived/toy_renders").exists() else None
    add("toy renders", "REGENERABLE" if rr and rr["proven"] else "KEEP", [B / "daisy/derived/toy_renders", B / "compare_renders"],
        "model_compare.render is deterministic", rr)
    add("stopped local round 4", "DROPPABLE", [B / "runs/r4_multires", B / "work/r4_multires"], "stopped at ~4% of epoch 1; no weights")
    add("failed Kaggle AMP realization", "DROPPABLE", [B / "daisy/kaggle_out3"], "NaN run; execution + hashes recorded in impact MMR")
    add("last.pt duplicates", "DROPPABLE", [*B.glob("runs/*/weights/last.pt")], "keep best.pt (one realization per run)")
    add("weights (best.pt)", "KEEP", [*B.glob("runs/*/weights/best.pt")], "one realization per behaviour class")
    return items


def summarize(items):
    agg = {}
    for i in items:
        a = agg.setdefault(i["class"], {"bytes": 0, "reclaimable_bytes": 0, "files": 0})
        for k in a:
            a[k] += i[k]
    return {k: {**v, "GB": round(v["bytes"] / 1e9, 3), "reclaimable_GB": round(v["reclaimable_bytes"] / 1e9, 3)} for k, v in agg.items()}


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser("baebugs-retention")
    ap.add_argument("scope", choices=["repo", "drive"])
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    items = repo_plan() if a.scope == "repo" else drive_plan()
    plan = {"scope": a.scope, "items": items, "summary": summarize(items),
            "proof_root": merkle_root(sorted(i["proof"]["root"] for i in items if i.get("proof", {}).get("root")))
            if any(i.get("proof", {}).get("root") for i in items) else None}
    Path(a.out).write_text(json.dumps(plan, indent=1, default=str))
    for i in items:
        pr = i.get("proof") or {}
        print(f"{i['class']:11s} {i['name']:38s} {i['bytes']/1e6:9.1f} MB  reclaimable {i['reclaimable_bytes']/1e6:9.1f} MB"
              + (f"  proof {pr.get('compared')} files, mismatch {pr.get('n_mismatch')}" if pr else ""))
    print(json.dumps(plan["summary"]))


if __name__ == "__main__":
    main()

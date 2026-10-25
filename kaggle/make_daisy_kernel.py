"""Build the Kaggle notebook + kernel-metadata for DAISY-BB-001 from the frozen
protocol JSON (daisy/DAISY-BB-001.json). The protocol JSON (dataset roots,
runs, settings, pinned baebugs commit) is embedded verbatim in the notebook and
its sha256 is checked at run time.

  python kaggle/make_daisy_kernel.py --user biobitworks --out kaggle/daisy_bb_001
"""
import argparse
import hashlib
import json
from pathlib import Path

import nbformat as nbf

CUSTODY = r'''
import hashlib, json, os
from pathlib import Path

def sha(p, chunk=1 << 20):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()

def leaf(rec):
    return hashlib.sha256(json.dumps(rec, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

from baebugs.explore import merkle_root

def find_member(bundle, name):
    for base in Path("/kaggle/input").glob(f"*{bundle}*"):
        for cand in [base / name, *base.glob(f"**/{name}")]:
            if (cand / "DAISY_POINTERS.jsonl").exists():
                return cand
    return None

MEMBERS, CUSTODY_REPORT = {}, {}
for bundle, names in PROTO["bundles"].items():
    for name in names:
        d = find_member(bundle, name)
        if d is None:
            raise SystemExit(f"CUSTODY FAIL: {bundle}/{name} not mounted")
        pts = [json.loads(l) for l in (d / "DAISY_POINTERS.jsonl").read_text().splitlines() if l.strip()]
        bad = [p["path"] for p in pts if not (d / p["path"]).exists() or sha(d / p["path"]) != p["sha256"]]
        root = merkle_root([leaf(p) for p in pts])
        ok = not bad and root == PROTO["roots"][name]
        CUSTODY_REPORT[name] = {"files": len(pts), "bad_files": len(bad), "root": root, "expected": PROTO["roots"][name], "ok": ok}
        print(f"{name:26s} files={len(pts):6d} bad={len(bad):3d} root_ok={root == PROTO['roots'][name]}")
        if not ok:
            raise SystemExit(f"CUSTODY FAIL (fail closed): {name} bad={bad[:3]} root={root}")
        MEMBERS[name] = d
print("custody: all members verified")
'''

TRAIN = r'''
import yaml, time, torch
from ultralytics import YOLO
WORK = Path("/kaggle/working/daisy"); WORK.mkdir(parents=True, exist_ok=True)
EVENTS = []
def event(kind, payload):
    rec = {"t": time.time(), "kind": kind, "payload": payload}
    rec["leaf"] = leaf({k: v for k, v in rec.items()})
    EVENTS.append(rec)
    with open(WORK / "events.jsonl", "a") as f:
        f.write(json.dumps(rec, default=str) + "\n")
event("custody", CUSTODY_REPORT)
event("protocol", {"sha256": PROTO_SHA, "id": PROTO["id"]})

def split_dirs(name, split):
    d = MEMBERS[name] / "images" / split
    return [str(d)] if d.exists() else []

def data_yaml(run, train_members, val_members):
    y = {"names": {0: "specimen"},
         "train": [p for m in train_members for p in split_dirs(m, "train")],
         "val": [p for m in val_members for p in split_dirs(m, "val")]}
    fp = WORK / f"{run}.yaml"; fp.write_text(yaml.safe_dump(y)); return fp

S = PROTO["settings"]
init = YOLO(S["model"]); init_sha = sha(S["model"]) if os.path.exists(S["model"]) else None
event("init_weights", {"model": S["model"], "sha256": init_sha, "torch": torch.__version__,
                       "cuda": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None})
RESULTS = {}
for run in PROTO["runs"]:
    name = run["name"]; t0 = time.time()
    dy = data_yaml(name, run["train"], run["val"])
    m = YOLO(S["model"])
    m.train(data=str(dy), epochs=S["epochs"], imgsz=S["imgsz"], batch=S["batch"], seed=S["seed"],
            deterministic=True, patience=10_000, project=str(WORK / "runs"), name=name, exist_ok=True,
            workers=S["workers"], plots=False, verbose=False)
    best = WORK / "runs" / name / "weights" / "best.pt"
    RESULTS[name] = {"train": run["train"], "val": run["val"], "weights_sha256": sha(best),
                     "minutes": round((time.time() - t0) / 60, 1), "status": "EXECUTED"}
    event("train_done", {"run": name, **RESULTS[name]})
    print(name, RESULTS[name])
'''

EVAL = r'''
import numpy as np, cv2
from baebugs.measure import YoloMeasurer

def val_metrics(weights, member, split):
    d = MEMBERS[member] / "images" / split
    if not d.exists():
        return None
    fp = WORK / f"eval_{member}_{split}.yaml"
    fp.write_text(yaml.safe_dump({"names": {0: "specimen"}, "train": str(d), "val": str(d)}))
    r = YOLO(weights).val(data=str(fp), imgsz=S["imgsz"], batch=S["batch"], plots=False, verbose=False,
                          project=str(WORK / "val"), name=f"{member}_{split}", exist_ok=True)
    return {"mask_map50_95": round(float(r.seg.map), 4), "mask_map50": round(float(r.seg.map50), 4),
            "box_map50_95": round(float(r.box.map), 4)}

def toy_size_error(weights):
    truth = json.loads((MEMBERS["toy_renders"] / "truth.json").read_text())
    meas = YoloMeasurer(weights, conf=0.15)
    out = {}
    for ppm in (10, 20):
        rows = [t for t in truth if t["px_per_mm"] == ppm]
        el, ew, det = [], [], 0
        for t in rows:
            img = cv2.imread(str(MEMBERS["toy_renders"] / t["image"]))
            ms = meas(img, ppm)
            if not ms:
                continue
            det += 1
            b = max(ms, key=lambda x: x.area_mm2)
            L, W = max(t["envelope_mm"][:2]), min(t["envelope_mm"][:2])
            el.append(abs(b.length_mm - L) / L); ew.append(abs(b.width_mm - W) / W)
        out[f"ppm{ppm}"] = {"n": len(rows), "detected": det,
                            "median_rel_len_err": round(float(np.median(el)), 4) if el else None,
                            "median_rel_wid_err": round(float(np.median(ew)), 4) if ew else None}
    return out

def ruler_truth_error(weights, member):
    tp = MEMBERS[member] / "truth_real_val.json"
    if not tp.exists():
        return None
    truth = json.loads(tp.read_text()); meas = YoloMeasurer(weights, conf=0.15)
    errs = []
    for t in truth:
        img = cv2.imread(str(MEMBERS[member] / t["image"]))
        if img is None or not t.get("objects"):
            continue
        ms = meas(img, t["px_per_mm"])
        for o in t["objects"]:
            if not ms:
                errs.append(1.0); continue
            b = min(ms, key=lambda x: (x.cx - o["cx"]) ** 2 + (x.cy - o["cy"]) ** 2)
            errs.append(abs(b.length_mm - o["length_mm"]) / o["length_mm"])
    return {"objects": len(errs), "median_rel_len_err": round(float(np.median(errs)), 4) if errs else None}

ALL_VAL = [n for b in PROTO["bundles"].values() for n in b if n not in ("toy_renders",)]
for name, res in RESULTS.items():
    w = str(WORK / "runs" / name / "weights" / "best.pt")
    res["eval"] = {m: val_metrics(w, m, "val") for m in ALL_VAL}
    res["toy"] = toy_size_error(w)
    res["toy_val"] = {f"ppm{p}": val_metrics(w, "toy_renders", f"ppm{p}") for p in (10, 20)}
    res["ruler_truth"] = {m: ruler_truth_error(w, m) for m in ("teacher_check", "teacher_check2")}
    res["status"] = "OBSERVED_EXPLORATORY"
    event("eval_done", {"run": name, "eval": res["eval"], "toy": res["toy"], "ruler_truth": res["ruler_truth"]})
    print(name, json.dumps(res["toy"]), json.dumps(res["ruler_truth"]))
'''

FINISH = r'''
root = merkle_root([e["leaf"] for e in EVENTS])
summary = {"protocol": PROTO["id"], "protocol_sha256": PROTO_SHA, "custody": CUSTODY_REPORT, "results": RESULTS,
           "events_root": root, "n_events": len(EVENTS),
           "admission": "no automatic promotion; best variant at most VALIDATION_CANDIDATE"}
(WORK / "results.json").write_text(json.dumps(summary, indent=1, default=str))
import shutil
for name in RESULTS:
    src = WORK / "runs" / name / "weights" / "best.pt"
    shutil.copy2(src, WORK / f"{name}_best.pt")
shutil.rmtree(WORK / "runs", ignore_errors=True); shutil.rmtree(WORK / "val", ignore_errors=True)
print("events root", root)
'''


def build(proto_path, out_dir, user):
    proto_txt = Path(proto_path).read_text()
    proto = json.loads(proto_txt)
    psha = hashlib.sha256(proto_txt.encode()).hexdigest()
    nb = nbf.v4.new_notebook()
    md, code = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
    nb.cells = [
        md(f"# {proto['id']} — DAISY verified-data training (baebugs)\n\nFrozen protocol: `daisy/DAISY-BB-001.md` + JSON "
           f"(sha256 `{psha}`). Gate 0 recomputes every staged file hash and member Merkle root and **stops on any mismatch**. "
           "Results are OBSERVED_EXPLORATORY; nothing is promoted automatically. Toy renders are parametric TOYS, not replicas."),
        code(f"!pip -q install ultralytics=={proto['settings']['ultralytics']} shapely trimesh manifold3d pyyaml\n"
             f"!pip -q install --no-deps git+https://github.com/biobitworks/baebugs.git@{proto['baebugs_commit']}"),
        code("import json, hashlib\nPROTO_TXT = " + json.dumps(proto_txt) +
             "\nPROTO = json.loads(PROTO_TXT)\nPROTO_SHA = hashlib.sha256(PROTO_TXT.encode()).hexdigest()\n"
             f"assert PROTO_SHA == {psha!r}, 'protocol changed'\nprint(PROTO['id'], PROTO_SHA)"),
        md("## Gate 0 — custody (fail closed)"), code(CUSTODY),
        md("## Frozen runs"), code(TRAIN),
        md("## Evaluation: every member val, toy renders (exact truth), ruler truth"), code(EVAL),
        md("## Outputs + event Merkle root"), code(FINISH),
    ]
    nb.metadata["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
    nb.metadata["language_info"] = {"name": "python"}
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    nbf.write(nb, out / "daisy_bb_001.ipynb")
    (out / "kernel-metadata.json").write_text(json.dumps({
        "id": f"{user}/baebugs-daisy-bb-001", "title": "baebugs DAISY-BB-001", "code_file": "daisy_bb_001.ipynb",
        "language": "python", "kernel_type": "notebook", "is_private": True, "enable_gpu": True,
        "enable_internet": True, "dataset_sources": [f"{user}/{b}" for b in proto["bundles"]],
        "competition_sources": [], "kernel_sources": []}, indent=1))
    return psha


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--proto", default="daisy/DAISY-BB-001.json")
    ap.add_argument("--out", default="kaggle/daisy_bb_001")
    ap.add_argument("--user", default="biobitworks")
    a = ap.parse_args()
    print(build(a.proto, a.out, a.user))

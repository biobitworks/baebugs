"""DAISY-BB-002 (amendment 1): split pseudo_specimens_r3_real by source collection.

Each r3 photo is traced to the GBIF collection it was copied from: its filename must exist in
<source>/images and the sha256 must match (byte identity), otherwise it is dropped as
unresolved. Labels and ruler truth are carried over unchanged (same teacher as r3).
  r3_ca          photos from gbif_ca_2 / gbif_specimen_images, original train/val split kept
  holdout_<st>   photos from gbif_<st>; all go to val (evaluation only)
Files are hardlinked when on the same volume. A report with per-set counts is written.
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from .retention import sha

DATASETS = "/Volumes/magicBLACKbox/baebugs/datasets"
SOURCES = {"ca": ["{D}/gbif_ca_2", "/Volumes/magicLABbox/baebugs/datasets/gbif_specimen_images"],
           "az": ["{D}/gbif_az"], "nv": ["{D}/gbif_nv"], "or": ["{D}/gbif_or"]}


def _img_dir(src):
    p = Path(src)
    return p / "images" if (p / "images").is_dir() else p


def _link(a, b):
    b.parent.mkdir(parents=True, exist_ok=True)
    if b.exists():
        b.unlink()
    try:
        os.link(a, b)
    except OSError:
        shutil.copy2(a, b)


def source_of(img, srcs):
    h = None
    for st, dirs in srcs.items():
        for d in dirs:
            cand = _img_dir(d) / img.name
            if cand.exists():
                h = h or sha(img)
                if sha(cand) == h:
                    return st
    return None


def build(datasets=DATASETS):
    D = Path(datasets); r3 = D / "pseudo_specimens_r3_real"
    srcs = {st: [s.format(D=D) for s in v] for st, v in SOURCES.items()}
    outs = {"ca": D / "r3_ca", **{st: D / f"holdout_{st}" for st in ("az", "nv", "or")}}
    for o in outs.values():
        if o.exists():
            shutil.rmtree(o)
    truth = {sp: json.loads((r3 / f"truth_real_{sp}.json").read_text()) for sp in ("train", "val")}
    tby = {sp: {Path(t["image"]).name: t for t in truth[sp]} for sp in truth}
    new_truth = {k: {"train": [], "val": []} for k in outs}
    rep = {k: {"train": 0, "val": 0} for k in outs}; rep["unresolved"] = []
    for sp in ("train", "val"):
        for img in sorted((r3 / "images" / sp).glob("*.jpg")):
            st = source_of(img, srcs)
            if st is None:
                rep["unresolved"].append(f"{sp}/{img.name}"); continue
            dsp = sp if st == "ca" else "val"
            o = outs[st]
            _link(img, o / "images" / dsp / img.name)
            lab = r3 / "labels" / sp / f"{img.stem}.txt"
            if lab.exists():
                _link(lab, o / "labels" / dsp / lab.name)
            if img.name in tby[sp]:
                t = dict(tby[sp][img.name]); t["image"] = f"images/{dsp}/{img.name}"
                new_truth[st][dsp].append(t)
            rep[st][dsp] += 1
    for st, o in outs.items():
        o.mkdir(parents=True, exist_ok=True)
        (o / "images" / "train").mkdir(parents=True, exist_ok=True)
        for sp in ("train", "val"):
            (o / f"truth_real_{sp}.json").write_text(json.dumps(new_truth[st][sp]))
        (o / "data.yaml").write_text(f"path: {o}\ntrain: images/train\nval: images/val\nnames:\n  0: specimen\n")
        (o / "SPLIT_REPORT.json").write_text(json.dumps({"set": o.name, "source_state": st, **rep[st],
                                                          "from": "pseudo_specimens_r3_real"}, indent=1))
    rep["n_unresolved"] = len(rep["unresolved"]); rep["unresolved"] = rep["unresolved"][:20]
    (D / "domain_split_report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if k != "unresolved"}))
    return rep


if __name__ == "__main__":
    build()

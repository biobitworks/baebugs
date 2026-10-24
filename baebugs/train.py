"""Train / fine-tune the YOLO sizer locally (Apple MPS, CUDA or CPU) and
benchmark sizing against ground truth.

  baebugs-train synth   --root /Volumes/magicLABbox/baebugs            # build synthetic set
  baebugs-train fit     --data <dir>/data.yaml --epochs 40               # train
  baebugs-train bench   --weights best.pt --truth <dir>/truth_val.json   # mm accuracy
  baebugs-train export-bugpicker --scan <scan_dir> --out <yolo_dir>      # real-data path
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import cv2
import numpy as np

DEFAULT_ROOT = os.environ.get("BAEBUGS_ROOT", "/Volumes/magicLABbox/baebugs")


def device():
    try:
        import torch
        if torch.backends.mps.is_available():
            return "mps"
        if torch.cuda.is_available():
            return 0
    except Exception:
        pass
    return "cpu"


def fit(data, model="yolo11n-seg.pt", epochs=40, imgsz=640, batch=16, project=None,
        name="baebugs-seg", **kw):
    from ultralytics import YOLO
    project = project or str(Path(DEFAULT_ROOT) / "runs")
    m = YOLO(model)
    m.train(data=str(data), epochs=epochs, imgsz=imgsz, batch=batch, device=device(),
            project=project, name=name, exist_ok=True, plots=True, verbose=False,
            mosaic=0.5, degrees=180, flipud=0.5, fliplr=0.5, **kw)
    best = Path(project) / name / "weights" / "best.pt"
    return best


def bench(weights, truth_json, max_images=None, match_mm=1.0):
    """Median relative length/width error and recall for YOLO, classical, and
    their consensus, against synthetic ground truth."""
    from .measure import YoloMeasurer, classical_measure, consensus
    truth = json.loads(Path(truth_json).read_text())[:max_images]
    root = Path(truth_json).parent
    yolo = YoloMeasurer(str(weights), conf=0.25) if weights else None
    stats = {k: {"L": [], "W": [], "found": 0} for k in ("yolo", "classical", "consensus")}
    n_true = 0
    for rec in truth:
        img = cv2.imread(str(root / rec["image"]))
        ppm = rec["px_per_mm"]
        sets = {"classical": classical_measure(img, ppm)}
        if yolo:
            sets["yolo"] = yolo(img, ppm)
            sets["consensus"] = [m for m in consensus(list(sets["yolo"]), list(sets["classical"]), ppm)
                                 if m.flag is None]
        for t in rec["objects"]:
            n_true += 1
            for k, ms in sets.items():
                if not ms:
                    continue
                d = [np.hypot(m.cx - t["cx"], m.cy - t["cy"]) for m in ms]
                i = int(np.argmin(d))
                if d[i] < match_mm * ppm:
                    stats[k]["found"] += 1
                    stats[k]["L"].append(abs(ms[i].length_mm / t["length_mm"] - 1))
                    stats[k]["W"].append(abs(ms[i].width_mm / t["width_mm"] - 1))
    out = {}
    for k, s in stats.items():
        if s["found"]:
            out[k] = {"recall": round(s["found"] / n_true, 3),
                      "median_len_err": round(float(np.median(s["L"])), 4),
                      "median_wid_err": round(float(np.median(s["W"])), 4),
                      "p90_wid_err": round(float(np.percentile(s["W"], 90)), 4)}
    out["n_true"] = n_true
    return out


def main(argv=None):
    ap = argparse.ArgumentParser("baebugs-train")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("synth"); s.add_argument("--root", default=DEFAULT_ROOT)
    s.add_argument("--n-train", type=int, default=300); s.add_argument("--n-val", type=int, default=60)
    f = sub.add_parser("fit"); f.add_argument("--data", required=True)
    f.add_argument("--model", default="yolo11n-seg.pt"); f.add_argument("--epochs", type=int, default=40)
    f.add_argument("--batch", type=int, default=16)
    b = sub.add_parser("bench"); b.add_argument("--weights"); b.add_argument("--truth", required=True)
    b.add_argument("--max-images", type=int)
    e = sub.add_parser("export-bugpicker"); e.add_argument("--scan", required=True)
    e.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "synth":
        from .synth_seg import build_dataset
        print(build_dataset(Path(a.root) / "datasets" / "synth_seg", a.n_train, a.n_val))
    elif a.cmd == "fit":
        print(fit(a.data, a.model, a.epochs, batch=a.batch))
    elif a.cmd == "bench":
        print(json.dumps(bench(a.weights, a.truth, a.max_images), indent=2))
    else:
        from .bugpicker_bridge import export_yolo
        print(export_yolo(a.scan, a.out))


if __name__ == "__main__":
    main()

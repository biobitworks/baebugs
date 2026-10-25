"""Freeze DAISY-BB-002 (source-domain holdout) as preregistered in daisy/DAISY-BB-002-prereg.md.

Inherits settings, gates and variance from DAISY-BB-001b unchanged; pins the prereg sha256,
the predecessor sha256 and the baebugs commit. Refuses to freeze unless every member used is
VERIFIED and the dataset summary reports zero train/val overlap.

  python kaggle/freeze_002.py --datasets /Volumes/magicBLACKbox/baebugs/daisy/datasets.json
"""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from baebugs.daisy_data import BUNDLES

SYN = ["synth_1_30_r2", "synth_1_30_r3_real", "synth_seg"]
PSE = ["pseudo_specimens_r3_real"]
H = {s: f"holdout_{s}" for s in ("az", "nv", "or")}
USE = ["baebugs-daisy-train", "baebugs-daisy-eval", "baebugs-daisy-holdout"]


def runs():
    base = SYN + PSE
    out = [{"name": "CA_dominant", "train": base, "val": base + list(H.values())}]
    for s, h in H.items():
        others = [H[o] for o in H if o != s]
        out.append({"name": f"LOSO_{s}", "train": base + others, "val": base + list(H.values()), "held_out": h})
    return out


def fsha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--datasets", required=True)
    ap.add_argument("--out", default="daisy/DAISY-BB-002.json")
    a = ap.parse_args()
    s = json.loads(Path(a.datasets).read_text()); ds = s["datasets"]
    need = {m for r in runs() for m in r["train"] + r["val"]} | {"toy_renders"}
    bad = {m: ds.get(m, {}).get("status") for m in need if ds.get(m, {}).get("status") != "VERIFIED"}
    if bad:
        raise SystemExit(f"refusing to freeze: not VERIFIED {bad}")
    if s["global_leakage"].get("train_val_overlap"):
        raise SystemExit(f"refusing to freeze: train/val overlap {s['global_leakage']}")
    bundles = {b: [m for m in BUNDLES[b] if ds.get(m, {}).get("status") == "VERIFIED"] for b in USE}
    staged = sorted({m for ms in bundles.values() for m in ms})
    prev = json.loads(Path("daisy/DAISY-BB-001b.json").read_text())
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    proto = {"id": "DAISY-BB-002", "status": "PROPOSED", "baebugs_commit": commit,
             "preregistration": {"path": "daisy/DAISY-BB-002-prereg.md", "sha256": fsha("daisy/DAISY-BB-002-prereg.md")},
             "predecessor": {"protocol": "DAISY-BB-001b", "sha256": fsha("daisy/DAISY-BB-001b.json")},
             "datasets_root": s["root"], "roots": {m: ds[m]["merkle_root"] for m in staged},
             "bundles": bundles, "runs": runs(),
             "settings": prev["settings"], "gates": prev["gates"], "variance": prev["variance"],
             "global_leakage": s["global_leakage"]}
    Path(a.out).write_text(json.dumps(proto, indent=1, sort_keys=True))
    print(a.out, commit, len(staged), "members")


if __name__ == "__main__":
    main()

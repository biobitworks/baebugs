"""Collect everything the dashboard compares into small JSON files under
dashboard/data/ (committed to the repo, so every number has a source):

  runs.json        per-run bench + per-epoch metrics, straight from ledger/*.jsonl
  database.json    reference size distributions (museum specimens via ruler, synthetic),
                   Essig family counts, DataONE/CIB sample types, kit class boundaries,
                   bench-analog size estimates
  (sweep/alerts/triage files are written by run_round4)
"""
from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path

import numpy as np

from .sieve import load_yaml


def runs(repo):
    out = {}
    for f in sorted(Path(repo, "ledger").glob("*.jsonl")):
        recs = [json.loads(l) for l in f.read_text().splitlines() if l.strip()]
        epochs = [{"epoch": r["payload"].get("epoch"),
                   **{k.split("/")[-1].replace("(M)", "_mask").replace("(B)", "_box"): v
                      for k, v in r["payload"].get("metrics", {}).items()
                      if "mAP50" in k or "loss" in k}}
                  for r in recs if r["step"].startswith("epoch_")]
        out[f.stem] = {"leaves": len(recs), "root": recs[-1]["root"] if recs else None,
                       "steps": [r["step"] for r in recs if not r["step"].startswith("epoch_")],
                       "bench": next((r["payload"] for r in reversed(recs) if r["step"] == "bench"), None),
                       "baseline_bench": next((r["payload"] for r in recs if r["step"] == "baseline_bench"), None),
                       "pseudo": next((r["payload"] for r in recs if r["step"] == "pseudo"), None),
                       "epochs": epochs}
    return out


def hist(vals, edges):
    c, _ = np.histogram(vals, bins=edges)
    return c.tolist()


def database(pseudo_dirs, synth_truth, essig_json=None, dataone_csv=None):
    edges = [0, 0.5, 1, 1.32, 2, 2.42, 3, 4.4, 5.5, 8, 12, 20, 30]
    real_w, real_l = [], []
    for d in pseudo_dirs:
        for split in ("train", "val"):
            p = Path(d) / f"truth_real_{split}.json"
            if p.exists():
                for rec in json.loads(p.read_text()):
                    for o in rec["objects"]:
                        real_w.append(o["width_mm"]); real_l.append(o["length_mm"])
    syn_w = []
    if synth_truth and Path(synth_truth).exists():
        syn_w = [o["width_mm"] for rec in json.loads(Path(synth_truth).read_text()) for o in rec["objects"]]
    db = {"width_edges_mm": edges,
          "museum_width_hist": hist(real_w, edges), "museum_n": len(real_w),
          "museum_width_pct": [round(float(np.percentile(real_w, q)), 2) for q in (10, 50, 90)] if real_w else None,
          "museum_length_pct": [round(float(np.percentile(real_l, q)), 2) for q in (10, 50, 90)] if real_l else None,
          "synthetic_width_hist": hist(syn_w, edges), "synthetic_n": len(syn_w),
          "kit_classes": load_yaml("insects.yaml")["classes"],
          "analog_estimates_mm": [  # rough typical widths; replace with AmScope measurements
              {"analog": "chia", "width": [1.0, 1.3]}, {"analog": "couscous", "width": [1.0, 1.5]},
              {"analog": "fideo", "width": [1.0, 1.5]}, {"analog": "white rice", "width": [1.8, 2.2]},
              {"analog": "brown/red/wild rice", "width": [1.5, 2.6]}, {"analog": "ditalini", "width": [7, 8]},
              {"analog": "campanelle", "width": [10, 15]}, {"analog": "farfalle", "width": [18, 22]}]}
    if essig_json and Path(essig_json).exists():
        fam = collections.Counter()
        for r in json.loads(Path(essig_json).read_text()):
            fam.update(r.get("families", {}))
        db["essig_top_families"] = fam.most_common(15)
        db["essig_records"] = sum(fam.values())
    if dataone_csv and Path(dataone_csv).exists():
        from .dataone_adapter import load_events, summary
        db["dataone_cib"] = summary(load_events(dataone_csv))
    return db


def main(argv=None):
    ap = argparse.ArgumentParser("baebugs-dashboard-data")
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--pseudo", nargs="*", default=[])
    ap.add_argument("--synth-truth")
    ap.add_argument("--essig")
    ap.add_argument("--dataone-csv")
    a = ap.parse_args(argv)
    out = Path(a.repo) / "dashboard" / "data"; out.mkdir(parents=True, exist_ok=True)
    (out / "runs.json").write_text(json.dumps(runs(a.repo), indent=1))
    (out / "database.json").write_text(json.dumps(database(a.pseudo, a.synth_truth, a.essig, a.dataone_csv), indent=1))
    print("wrote", out)


if __name__ == "__main__":
    main()

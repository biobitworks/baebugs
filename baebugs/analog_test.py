"""Novel-insect test with food analogs that are in NO insect database.

Expectation: none of the analogs should come out KNOWN. A confident detection
outside the database's size/shape range is NOVEL (VIP); something the insect
teacher doesn't recognise is UNKNOWN. Anything marked KNOWN is a miss the
human-review lane would let through.

Per photo:
  1. scale  - ruler px/mm; for tilted photos a LOCAL scale: the mm-tick period is
              measured in short windows along the ruler and fitted against position,
              so each object gets the px/mm at its own height (perspective).
  2. objects- analogs found with YOLOE prompted for grains/seeds/pasta (reference list).
  3. system - the production path: trained student (YOLO) + zero-shot 'insect'
              teacher (YOLOE) -> consensus -> triage vs the database reference.
  4. join   - every analog object gets the system's verdict (known/unknown/novel/missed)
              and a real mm size, which replaces the estimates table.
"""
from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np


def _ac_period(prof, lo=2.0, hi=40.0):
    prof = prof - np.convolve(prof, np.ones(41) / 41, mode="same")
    n = len(prof)
    f = np.fft.rfft(prof, 2 * n)
    ac = np.fft.irfft(f * np.conj(f))[:n]
    ac = ac / (ac[0] + 1e-9)
    a, b = int(lo), min(int(hi) + 2, n - 2)
    seg = ac[a:b]
    if seg.size < 3:
        return None, 0.0
    pk = [i for i in range(1, len(seg) - 1) if seg[i] >= seg[i - 1] and seg[i] >= seg[i + 1] and seg[i] > 0.5 * seg.max()]
    if not pk:
        return None, 0.0
    i = pk[0]
    p, q, r = seg[i - 1], seg[i], seg[i + 1]
    return a + i + 0.5 * (p - r) / (p - 2 * q + r + 1e-9), float(q)


def local_ruler_scale(img, win=260, step=130):
    """Find the ruler's tick edges (vertical or horizontal), measure the tick
    period in sliding windows along each, keep the FINER edge (mm, not 1/16 in),
    and fit period = a + b*position. Returns (ppm_at(pos) callable, axis, diag)."""
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    best = None
    for axis, reg in (("y", g.T), ("x", g)):   # axis = image axis the ruler runs along
        energy = np.abs(np.diff(reg, axis=1)).mean(axis=1)
        order = np.argsort(energy)[::-1]
        bands = []
        for c in order:
            if all(abs(c - b) > 12 for b in bands):
                bands.append(int(c))
            if len(bands) >= 4:
                break
        for c in bands:
            pos, per, q = [], [], []
            for s in range(0, reg.shape[1] - win, step):
                prof = reg[max(0, c - 2):c + 3, s:s + win].mean(axis=0)
                p, conf = _ac_period(prof)
                if p and conf > 0.3:
                    pos.append(s + win / 2); per.append(p); q.append(conf)
            if len(per) < 4:
                continue
            pos, per = np.array(pos), np.array(per)
            b, a = np.polyfit(pos, per, 1)
            resid = np.abs(per - (a + b * pos))
            keep = resid < max(0.6, 2.5 * np.median(resid))
            if keep.sum() >= 4:
                b, a = np.polyfit(pos[keep], per[keep], 1)
            fit_err = float(np.median(np.abs(per[keep] - (a + b * pos[keep]))) / np.median(per[keep]))
            cand = {"axis": axis, "band": c, "a": float(a), "b": float(b), "n": int(keep.sum()),
                    "median_period": float(np.median(per[keep])), "fit_rel_err": round(fit_err, 4),
                    "mean_conf": round(float(np.mean(q)), 3)}
            # prefer many consistent windows, then the finer period (mm over 1/16 inch)
            score = (cand["n"] >= 6, -fit_err > -0.08, -cand["median_period"])
            if best is None or score > best[0]:
                best = (score, cand)
    if best is None:
        return None, None, {}
    c = best[1]
    return (lambda pos: c["a"] + c["b"] * pos), c["axis"], c


def run(image_paths, student_weights, ref_truths, out_dir, analog_prompts=("rice grain", "seed", "pasta"),
        insect_prompts=("insect",)):
    from .measure import YoloMeasurer, consensus, _from_contour
    from .specimen_photo import segment_yoloe
    from .triage import reference_from_truth, triage
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    ref_L, ref_W = reference_from_truth(*ref_truths)
    student = YoloMeasurer(str(student_weights), conf=0.15)
    report = []
    for p in image_paths:
        img = cv2.imread(str(p))
        name = Path(p).name
        ppm_at, axis, diag = local_ruler_scale(img)
        has_scale = ppm_at is not None and diag.get("fit_rel_err", 1) < 0.03 and diag.get("n", 0) >= 6  # serrated dish rims fit ~6%, rulers <2%
        ref_ppm = float(np.median([ppm_at(v) for v in np.linspace(0, img.shape[0 if axis == "y" else 1], 9)])) if has_scale else 10.0
        # reference list of analog objects (prompted for food, not insects)
        polys, objs = segment_yoloe(img, ref_ppm, prompts=analog_prompts, conf=0.15,
                                    min_area_mm2=0.2, length_range=(0.3, 60))
        # production path at the image's median scale
        a = student(img, ref_ppm)
        _, b = segment_yoloe(img, ref_ppm, prompts=insect_prompts, length_range=(0.3, 60))
        ms = consensus(a, b, ref_ppm, match_mm=2.0) if (a or b) else []
        verdicts = triage(ms, ref_L, ref_W, image=name)
        rows, vis = [], img.copy()
        for poly, o in zip(polys, objs):
            # rescale this object's size with the LOCAL ruler scale at its position
            loc = ppm_at(o.cy if axis == "y" else o.cx) if has_scale else None
            k = (ref_ppm / loc) if loc else 1.0
            L, W = o.length_mm * k, o.width_mm * k
            near = [v for v in verdicts if np.hypot(v.cx - o.cx, v.cy - o.cy) < max(2.0 * ref_ppm, 0.5 * o.length_mm * ref_ppm)]
            v = min(near, key=lambda v: np.hypot(v.cx - o.cx, v.cy - o.cy)) if near else None
            status = v.status if v else "missed"
            rows.append({"image": name, "cx": round(o.cx), "cy": round(o.cy),
                         "length_mm": round(L, 2) if has_scale else None,
                         "width_mm": round(W, 2) if has_scale else None,
                         "scale": "local ruler" if has_scale else "none",
                         "system_status": status, "priority": v.priority if v else "none",
                         "reasons": v.reasons if v else ["not detected by the production path"],
                         "teacher_conf": round(o.conf, 3)})
            col = {"known": (0, 160, 0), "unknown": (0, 165, 255), "novel": (0, 0, 230), "missed": (160, 160, 160)}[status]
            cv2.polylines(vis, [poly.astype(np.int32)], True, col, 2)
            if has_scale:
                cv2.putText(vis, f"{status} {L:.1f}x{W:.1f}", (int(o.cx) + 4, int(o.cy) - 4),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, col, 1, cv2.LINE_AA)
        cv2.imwrite(str(out / f"annotated_{name}"), vis, [cv2.IMWRITE_JPEG_QUALITY, 85])
        report.append({"image": name, "scale": diag if has_scale else None, "objects": rows,
                       "system_detections": len(ms),
                       "summary": {s: sum(r["system_status"] == s for r in rows) for s in ("known", "unknown", "novel", "missed")}})
    (out / "report.json").write_text(json.dumps(report, indent=1))
    return report


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser("baebugs-analog-test")
    ap.add_argument("--images", nargs="+", required=True)
    ap.add_argument("--weights", required=True)
    ap.add_argument("--ref", nargs="+", required=True, help="truth JSONs that define the database reference")
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    rep = run(a.images, a.weights, a.ref, a.out)
    for r in rep:
        print(r["image"], "scale:", "local ruler" if r["scale"] else "none", r["summary"])


if __name__ == "__main__":
    main()

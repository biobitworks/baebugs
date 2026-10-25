"""Boxes for the bench assets in their photos, from an open-vocabulary detector (YOLOE text prompts).

These are INFERRED, not labels: each box records the model (weights sha256), the prompt list (hash), the confidence,
and the photo's tier-tree frame root (baebugs.tiers), so a person can confirm or correct it later. Confirmed boxes
become training labels for a bench/labware detector; unconfirmed ones never do.

  python -m baebugs.asset_boxes --weights yoloe-11s-seg.pt
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

PROMPTS = ["tube rack", "pipette tip box", "microplate", "cryovial", "conical tube", "plastic tub", "robot arm",
           "orange 3D printed shelf rack", "wooden post", "breadboard", "steel ruler", "metal frame", "vortex mixer",
           "3D printer", "printed tray frame", "hexagonal grid", "perforated metal sheet", "plastic box"]


def run(weights, conf=0.25, repo="."):
    import cv2
    from ultralytics import YOLOE

    from . import tiers as T
    m = YOLOE(weights)
    m.set_classes(PROMPTS, m.get_text_pe(PROMPTS))
    wsha = hashlib.sha256(Path(weights).read_bytes()).hexdigest()
    photos = json.loads(Path(repo, "assets/photos.json").read_text())
    out = []
    for p in photos:
        if not p.get("file"):
            continue
        img = cv2.imread(str(Path(repo, p["file"])))
        r = m.predict(img, conf=conf, verbose=False)[0]
        boxes = [{"prompt": PROMPTS[int(c)], "conf": round(float(s), 3), "bbox": [int(v) for v in b]}
                 for b, c, s in zip(r.boxes.xyxy.tolist(), r.boxes.cls.tolist(), r.boxes.conf.tolist())]
        fr = T.frame(img, [{"id": f"{i}:{b['prompt']}", "bbox": b["bbox"], "label": b["prompt"], "score": b["conf"]}
                           for i, b in enumerate(boxes)], meta={"photo": p["photo_id"], "source": "asset photo"})
        out.append({"photo_id": p["photo_id"], "published_sha256": p["published_sha256"], "frame_root": fr["root"],
                    "pixel_root": fr["pixel_root"], "objects_root": fr["objects_root"], "boxes": boxes})
    rec = {"status": "INFERRED (unconfirmed; not training labels)", "model": Path(weights).name, "weights_sha256": wsha,
           "prompts": PROMPTS, "prompts_sha256": hashlib.sha256(json.dumps(PROMPTS).encode()).hexdigest(), "conf_min": conf,
           "photos": out}
    Path(repo, "assets/boxes.json").write_text(json.dumps(rec, indent=1))
    return rec


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--weights", default="yoloe-11s-seg.pt"); ap.add_argument("--conf", type=float, default=0.25)
    a = ap.parse_args()
    r = run(a.weights, a.conf)
    print(json.dumps({x["photo_id"]: len(x["boxes"]) for x in r["photos"]}))

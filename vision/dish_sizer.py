"""First-pass object sizing for a petri dish photo.

Finds the dish, separates objects from the background by colour difference,
and measures each object's length and width (the short side is what decides
whether it fits through a filter's holes).

Usage: python dish_sizer.py IMAGE --px-per-mm 9.18 [--out annotated.png] [--json objects.json]
"""
import argparse
import json

import cv2
import numpy as np


def find_dish(img):
    """Return (cx, cy, r) of the dish's strongest circular edge, or None.

    The dish has several concentric rings (rim, wall), so only the centre is reliable.
    """
    gray = cv2.medianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), 5)
    w = gray.shape[1]
    circles = cv2.HoughCircles(
        gray, cv2.HOUGH_GRADIENT, dp=1.5, minDist=w,
        param1=100, param2=40, minRadius=int(0.25 * w), maxRadius=int(0.6 * w),
    )
    if circles is None:
        return None
    cx, cy, r = circles[0][0]
    return int(cx), int(cy), int(r)


def colour_distance(diff, shadow_weight):
    """CIELAB distance with darkening down-weighted: shadows make the background darker but keep its colour.

    Getting lighter is not down-weighted, so pale objects (pasta, rice) still stand out.
    """
    diff = diff.copy()
    darker = diff[..., 0] < 0
    diff[..., 0][darker] *= shadow_weight
    return np.linalg.norm(diff, axis=-1)


def fit_background(lab, mask, threshold, shadow_weight, iterations=4):
    """Background colour over the dish as a smooth quadratic surface per CIELAB channel.

    Models gradual lighting changes across the dish. Each pass refits without the pixels that stood
    out from the previous fit (objects, shadows), so even big objects don't drag the background.
    """
    h, w = mask.shape
    ys, xs = np.nonzero(mask)
    step = max(1, len(xs) // 40000)
    ys, xs = ys[::step], xs[::step]

    def terms(x, y):
        x, y = (x - w / 2) / w, (y - h / 2) / h
        return np.stack([np.ones_like(x), x, y, x * x, x * y, y * y], axis=-1)

    a, samples = terms(xs.astype(float), ys.astype(float)), lab[ys, xs]
    keep = np.ones(len(xs), bool)
    for _ in range(iterations):
        coef, *_ = np.linalg.lstsq(a[keep], samples[keep], rcond=None)
        keep = colour_distance(samples - a @ coef, shadow_weight) < threshold
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    return (terms(xx, yy) @ coef).astype(np.float32)


def segment(img, mask, threshold, shadow_weight):
    """Mark pixels whose colour differs from the background by more than `threshold` (CIELAB units)."""
    lab = cv2.cvtColor(cv2.GaussianBlur(img, (5, 5), 0), cv2.COLOR_BGR2LAB).astype(np.float32)
    distance = colour_distance(lab - fit_background(lab, mask, threshold, shadow_weight), shadow_weight)
    objects = ((distance > threshold) & (mask > 0)).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    objects = cv2.morphologyEx(objects, cv2.MORPH_OPEN, kernel)
    objects = cv2.morphologyEx(objects, cv2.MORPH_CLOSE, kernel, iterations=2)
    return objects, distance


def measure(objects, px_per_mm, min_area_mm2):
    contours, _ = cv2.findContours(objects, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    results = []
    for c in contours:
        area_mm2 = cv2.contourArea(c) / px_per_mm**2
        if area_mm2 < min_area_mm2:
            continue
        (cx, cy), (a, b), angle = cv2.minAreaRect(c)
        results.append({
            "center_px": [round(cx), round(cy)],
            "length_mm": round(max(a, b) / px_per_mm, 1),
            "width_mm": round(min(a, b) / px_per_mm, 1),
            "area_mm2": round(area_mm2, 1),
            "box_px": cv2.boxPoints(((cx, cy), (a, b), angle)).round().astype(int).tolist(),
            "contour": c,
            "rect": ((cx, cy), (a, b), angle),
        })
    results.sort(key=lambda o: -o["area_mm2"])
    for i, o in enumerate(results, start=1):
        o["id"] = i
    return results


def annotate(img, dish, inner_r, results):
    out = img.copy()
    if dish:
        cv2.circle(out, dish[:2], inner_r, (255, 200, 0), 1)
    for o in results:
        cv2.drawContours(out, [o["contour"]], -1, (0, 255, 0), 2)
        box = cv2.boxPoints(o["rect"]).astype(int)
        cv2.drawContours(out, [box], -1, (255, 0, 255), 1)
        x, y = o["center_px"]
        label = f"#{o['id']} {o['length_mm']}x{o['width_mm']}mm"
        cv2.putText(out, label, (x + 12, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 3)
        cv2.putText(out, label, (x + 12, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--px-per-mm", type=float, required=True)
    ap.add_argument("--threshold", type=float, default=20, help="colour difference from background (CIELAB)")
    ap.add_argument("--floor-mm", type=float, default=48, help="diameter of the dish floor to analyse, mm (63 mm dish: wall starts at ~48 mm)")
    ap.add_argument("--shadow-weight", type=float, default=0.5, help="weight of darkening vs colour change (shadows only darken)")
    ap.add_argument("--min-area", type=float, default=0.5, help="ignore blobs smaller than this, mm^2")
    ap.add_argument("--out", default="annotated.png")
    ap.add_argument("--json")
    args = ap.parse_args()

    img = cv2.imread(args.image)
    if img is None:
        raise SystemExit(f"cannot read {args.image}")
    dish = find_dish(img)
    mask = np.zeros(img.shape[:2], np.uint8)
    if dish:
        inner_r = int(args.floor_mm / 2 * args.px_per_mm)
        cv2.circle(mask, dish[:2], inner_r, 255, -1)
        print(f"dish: center {dish[:2]}, analysing {args.floor_mm:g} mm across")
    else:
        inner_r = 0
        mask[:] = 255
        print("dish not found; analysing the whole image")

    objects, _ = segment(img, mask, args.threshold, args.shadow_weight)
    results = measure(objects, args.px_per_mm, args.min_area)
    cv2.imwrite(args.out, annotate(img, dish, inner_r, results))

    print(f"{len(results)} objects")
    for o in results:
        print(f"  #{o['id']}: {o['length_mm']} x {o['width_mm']} mm, area {o['area_mm2']} mm2, at {o['center_px']}")
    if args.json:
        with open(args.json, "w") as f:
            json.dump([{k: v for k, v in o.items() if k not in ("contour", "rect")} for o in results], f, indent=2)


if __name__ == "__main__":
    main()
